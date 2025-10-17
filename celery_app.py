import asyncio
import celery
from utils.brevo import sendOtpEmail
from utils.anchor import createAnchorCustomer, getAnchorCustomer, validateAnchoTier2Kyc, validateAnchorTier3Kyc, uploadAnchorCustomerDocument, createAnchorDepositAccount
from utils.minio import download_s3_object, download_s3_object_for_requests
import schemas
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import model
from config import settings
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Callback-enabled task base
class CallbackTask(celery.Task):
    def on_success(self, retval, task_id, args, kwargs):  # noqa: D401
        try:
            notifyTaskCompletion.delay(
                task_name=self.name,
                task_id=task_id,
                status="success",
                result=retval,
                error=None,
                extra={"args": args, "kwargs": kwargs}
            )
        except Exception:
            # Avoid raising inside lifecycle hook
            pass

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: D401
        try:
            notifyTaskCompletion.delay(
                task_name=self.name,
                task_id=task_id,
                status="failed",
                result=None,
                error=str(exc),
                extra={"args": args, "kwargs": kwargs, "traceback": str(einfo)}
            )
        except Exception:
            pass

# Configure Celery with RabbitMQ as broker and RPC as backend
celery_app = celery.Celery(
    'task',
    broker=settings.RABBITMQ_URL,  # RabbitMQ for message queuing
    backend='rpc://',  # RPC backend for result storage
    result_expires=3600,  # Results expire after 1 hour
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Configure RabbitMQ persistence and retry settings
celery_app.conf.update(
    # Message persistence
    task_default_delivery_mode=2,  # Persistent messages
    task_acks_late=True,  # Acknowledge after processing
    task_reject_on_worker_lost=True,  # Reject if worker is lost
    
    # Retry configuration
    task_default_retry_delay=300,  # 5 minutes default retry delay
    task_max_retries=3,  # Maximum 3 retries
    task_retry_jitter=True,  # Add randomness to retry timing
    task_retry_backoff=True,  # Exponential backoff
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_compression='gzip',  # Compress large messages
    task_ignore_result=False,  # Store results in RabbitMQ
    
    # Queue routing
    task_routes={
        'create_anchor_account_task': {'queue': 'anchor_queue'},
        'validate_kyc_task': {'queue': 'kyc_queue'},
        'link_anchor_account_task': {'queue': 'anchor_queue'},
        'send_otp_task': {'queue': 'otp_queue'},
        'kyc_verification_task': {'queue': 'kyc_queue'},
        'monitor_failed_tasks': {'queue': 'monitor_queue'},
        'create_anchor_deposit_account_task': {'queue': 'anchor_queue'},
    },
    
    # Define durable queues for persistence
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
            'durable': True,
            'auto_delete': False,
        },
        'anchor_queue': {
            'exchange': 'anchor_exchange',
            'routing_key': 'anchor',
            'durable': True,
            'auto_delete': False,
        },
        'kyc_queue': {
            'exchange': 'kyc_exchange',
            'routing_key': 'kyc',
            'durable': True,
            'auto_delete': False,
        },
        'otp_queue': {
            'exchange': 'otp_exchange',
            'routing_key': 'otp',
            'durable': True,
            'auto_delete': False,
        },
        'monitor_queue': {
            'exchange': 'monitor_exchange',
            'routing_key': 'monitor',
            'durable': True,
            'auto_delete': False,
        }
    },
    
    # Task result settings for RPC backend
    result_persistent=False,  # RPC doesn't persist results
    result_cache_max=10000,  # Cache up to 10k results
    result_expires=3600,  # Results expire after 1 hour
)

async def linkAnchorAccount(anchor_customer_id: str, user_id: int):
    db = SessionLocal()
    try:
        user = db.get(model.User, user_id)
        if not user:
            raise Exception(f"User not found for user_id: {user_id}")

        if user.anchor_user:
            return user.id
        else:
            anchor_user = model.AnchorUser(user_id=user.id, anchor_customer_id=anchor_customer_id)
            db.add(anchor_user)
            db.commit()
            db.refresh(anchor_user)
            logger.info(f"Anchor account linked successfully for user_id: {user_id}")
            return user.id
    except Exception as e:
        db.rollback()
        logger.error(f"Error linking anchor account for user_id: {user_id}: {str(e)}")
        raise Exception(f"Anchor account linking failed: {str(e)}")
    finally:
        db.close()

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='send_otp_task'
)
def sendOtpTask(self, otp: str, email: str, type: str):
    """
    Send OTP task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    try:
        logger.info(f"Attempting to send OTP to {email} (attempt {self.request.retries + 1})")
        response = asyncio.run(sendOtpEmail(otp=otp, email=email, otpType=schemas.OtpType(type)))
        
        if response not in [200, 201]:
            raise Exception(f"OTP sending failed with status code: {response}")
        
        logger.info(f"OTP sent successfully to {email}")
        return {
            'status': 'success',
            'email': email,
            'otp_type': type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"OTP sending failed for {email}: {str(exc)}")
        raise self.retry(exc=exc, countdown=300, max_retries=3)

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='create_anchor_account_task'
)
def createAnchorAccountTask(
    self,
    firstName: str,
    lastName: str,
    addressLine_1: str,
    city: str,
    state: schemas.NigeriaState,
    postalCode: str,
    email: str,
    phoneNumber: str,
    dateOfBirth: datetime,
    gender: str,
    bvn: str,
    selfieImage: str,
    idType: schemas.IDType,
    idNumber: str,
    idExpirationDate: datetime,
    addressLine_2: Optional[str],
    middleName: Optional[str],
    maidenName: Optional[str],
    mode: schemas.AnchorMode,
):
    """
    Create Anchor account task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    try:
        logger.info(f"Attempting to create Anchor account for {email} (attempt {self.request.retries + 1})")
        
        response = asyncio.run(createAnchorCustomer(data=locals(), mode=schemas.AnchorMode(mode)))
        
        if response.status_code in [201, 200]:
            logger.info(f"Anchor account created successfully for {email}")
            return {
            'status': 'success',
            'email': email,
            'anchor_response': response.json(),
            'timestamp': datetime.utcnow().isoformat()
            }
        elif response.status_code == 500:
            logger.error(f"Anchor API error: {response.status_code} - {response.text}")
            raise self.retry(exc=Exception(f"Anchor API error: {response.status_code} - {response.text}"), countdown=300, max_retries=1)
        else:
            logger.error(f"Anchor account creation failed for {email}: {response.status_code} - {response.text}")
        
    except Exception as exc:
        logger.error(f"Anchor account creation failed for {email}: {str(exc)}")

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='validate_kyc_tier2_task'
)
def validateAnchorTier2KycTask(self, anchor_customer_id: str, mode: schemas.AnchorMode):
    """
    Validate KYC task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    logger.info(f"Attempting to validate KYC for {anchor_customer_id} (attempt {self.request.retries + 1})")
    kyc =asyncio.run(validateAnchoTier2Kyc(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode(mode)))
    if kyc.get('code') in [200, 201]:
        logger.info(f"KYC validated successfully for {anchor_customer_id}")
        return {
            'status': 'success',
            'anchor_customer_id': anchor_customer_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    elif kyc.get('code') == 500:
        logger.error(f"Unable to reach Anchor API: {kyc}")
        raise self.retry(exc=Exception(f"Unable to reach Anchor API: {kyc}"), countdown=1800, max_retries=3)
    else:
        logger.error(f"KYC validation failed for {anchor_customer_id}: {kyc}")
        raise Exception(f"KYC validation failed for {anchor_customer_id}: status code {kyc.get('code')}")

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='validate_kyc_task'
)
def validateAnchorTier3KycTask(self, anchor_customer_id: str, mode: schemas.AnchorMode):
    """
    Validate KYC task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    logger.info(f"Attempting to validate KYC for {anchor_customer_id} (attempt {self.request.retries + 1})")
    kyc =asyncio.run(validateAnchorTier3Kyc(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode(mode)))
    if kyc.get('code') in [200, 201]:
        logger.info(f"KYC validated successfully for {anchor_customer_id}")
        return {
            'status': 'success',
            'anchor_customer_id': anchor_customer_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    elif kyc.get('code') == 500:
        logger.error(f"Unable to reach Anchor API: {kyc.get('error')}")
        raise self.retry(exc=Exception(f"Unable to reach Anchor API: {kyc.get('error')}"), countdown=300, max_retries=5)
    else:
        logger.error(f"KYC validation failed for {anchor_customer_id}: {kyc.get('error')}")
        raise Exception(f"KYC validation failed for {anchor_customer_id}: {kyc.get('error')}")

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='upload_kyc_file_task'
)
def uploadAnchorKycDocumentTask(self, anchor_customer_id: str, document_id: str, user_id, mode: schemas.AnchorMode):
    """
    Upload KYC file task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    logger.info(f"Attempting to upload KYC file for {anchor_customer_id} (attempt {self.request.retries + 1})")
    s3_file_data = asyncio.run(download_s3_object_for_requests(bucket_name="user", object_name=f"{user_id}/kyc/{schemas.UserDocumentType.FRONT_ID.value}"))
    file_data = { "fileData": s3_file_data }
    upload_request = asyncio.run(uploadAnchorCustomerDocument(anchor_customer_id=anchor_customer_id, document_id=document_id, file_data=file_data, mode=schemas.AnchorMode(mode)))
    if upload_request.get('code') in [200, 201]:
        logger.info(f"KYC file uploaded successfully for {anchor_customer_id}")
        return {
        'status': 'success',
        'anchor_customer_id': anchor_customer_id,
        'document_id': document_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    elif upload_request.get('code') == 500:
        logger.error(f"Unable to reach Anchor API: {upload_request.get('error')}")
        raise self.retry(exc=Exception(f"Unable to reach Anchor API: {upload_request.get('error')}"), countdown=300, max_retries=5)
    else:
        logger.error(f"Failed to upload KYC file for {anchor_customer_id}: {upload_request.get('error')}")

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='kyc_verification_task'
)
def createAnchorDepositAccountTask(self, anchor_customer_id: str, email: str, mode: schemas.AnchorMode):
    """
    KYC verification task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    logger.info(f"Attempting to verify KYC for anchor_customer_id: {anchor_customer_id} (attempt {self.request.retries + 1})")

    db = SessionLocal()
    user = db.execute(select(model.User).where(model.User.email == email)).scalar_one_or_none()
    if user is None:
        raise Exception(f"User not found for email: {email}")
    
    user.kyc.verified = True
    try:
        db.add(user)
        db.commit()
        logger.info(f"KYC verified successfully for user_id: {user.id}")
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to verify KYC for user_id: {user.id}: {str(e)}")
    finally:
        db.close()
    
    # create anchor deposit account
    logger.info(f"Attempting to create Anchor deposit account for {anchor_customer_id} (attempt {self.request.retries + 1})")
    status_code = asyncio.run(createAnchorDepositAccount(anchor_customer_id=anchor_customer_id, mode=schemas.AnchorMode(mode)))
    if status_code.get('code') in [200, 201]:
        logger.info(f"Anchor deposit account created successfully for {anchor_customer_id}")
        return {
            'status': 'success',
            'user_id': user.id,
            'anchor_customer_id': anchor_customer_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    elif status_code.get('code') == 500:
        logger.error(f"Unable to reach Anchor API: {status_code.get('error')}")
        raise self.retry(exc=Exception(f"Unable to reach Anchor API: {status_code.get('error')}"), countdown=1800, max_retries=3)
    else:
        logger.error(f"Failed to create Anchor deposit account for {anchor_customer_id}: status code {status_code.get('code')}")
        raise Exception(f"Failed to create Anchor deposit account for {anchor_customer_id}: status code {status_code.get('code')}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
    retry_jitter=True,
    name='link_anchor_account_task'
)
def linkAnchorAccountTask(self, **kwargs):
    """
    Link Anchor account task with retry logic
    Retries: 3 times with 5-minute intervals
    Results stored in RabbitMQ
    """
    anchor_customer_id = kwargs.get('anchor_customer_id')
    anchor_deposit_account_id = kwargs.get('anchor_deposit_account_id')
    email = kwargs.get('email')
    mode = kwargs.get('mode')
    
    try:
        logger.info(f"Attempting to link Anchor account for anchor_customer_id: {anchor_customer_id} (attempt {self.request.retries + 1})")

        db = SessionLocal()
        user = db.execute(select(model.User).where(model.User.email == email)).scalar_one_or_none()
        if user is None:
            raise Exception(f"User not found for email: {email}")

        if not user.anchor_user:
        
            user.anchor_user = model.AnchorUser(customerId=anchor_customer_id, depositAccountId=anchor_deposit_account_id)
        else:
            user.anchor_user.customerId = anchor_customer_id
            user.anchor_user.depositAccountId = anchor_deposit_account_id

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Anchor account linked successfully for user_id: {user.id}")
        # notify user about Anchor account
        return {
            'status': 'success',
            'user_id': user.id,
            'anchor_customer_id': anchor_customer_id,
            'anchor_deposit_account_id': anchor_deposit_account_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to link Anchor account for user_id: {user.id}: {str(e)}")
    finally:
        db.close()

# Task monitoring and management
@celery_app.task(
    bind=True,
    name='monitor_failed_tasks'
)
def monitorFailedTasks(self):
    """
    Monitor and report failed tasks
    Results stored in RabbitMQ
    """
    try:
        logger.info("Starting failed tasks monitoring")
        
        # Get failed tasks from the last hour
        failed_tasks = celery_app.control.inspect().failed()
        
        failed_count = 0
        if failed_tasks:
            for worker, tasks in failed_tasks.items():
                failed_count += len(tasks)
                for task in tasks:
                    logger.error(f"Failed task {task['id']}: {task['name']} - {task['exception']}")
        
        result = {
            'status': 'monitoring_complete',
            'failed_count': failed_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Monitoring complete. Found {failed_count} failed tasks")
        return result
        
    except Exception as exc:
        logger.error(f"Monitoring failed: {str(exc)}")
        return {
            'status': 'monitoring_failed',
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }

if __name__ == '__main__':
    celery_app.start()


@celery_app.task(name='notify_task_completion')
def notifyTaskCompletion(task_name: str, task_id: str, status: str, result=None, error: str | None = None, extra: dict | None = None):
    """Callback task to persist/report task outcomes.

    You can extend this to:
    - write to DB (e.g., a TaskLog table)
    - emit webhooks/Slack notifications
    - push metrics
    """
    payload = {
        'task_name': task_name,
        'task_id': task_id,
        'status': status,
        'result': result,
        'error': error,
        'extra': extra or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    try:
        logger.info(f"Task callback: {payload}")
        # Example: persist to database if needed
        # db = SessionLocal(); ... db.add(TaskLog(...)); db.commit(); db.close()
    except Exception as e:
        logger.error(f"Failed to handle task callback for {task_id}: {e}")
    return payload