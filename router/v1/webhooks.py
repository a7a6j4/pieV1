from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update
from database import db
import model
from utils.anchor import createAnchorDepositAccount
from utils.brevo import sendEmail
from utils.kyc.anchor import sendKycDocumentsToAnchor, sendTierThreeKycRequest, sendTierTwoKycRequest
from utils.minio import get_file_object

webhooks = APIRouter(
    prefix="/webhook",
    tags=["webhook"]
)

@webhooks.post("/anchor")
async def anchorWebhook(db: db, data: dict):

    event = data.get("data").get("type")

    if event == "accountNumber.created":

        anchor_customer_id = data.get("included")[1].get("relationships").get("customer").get("data").get("id")
        user = db.execute(select(model.User).join(model.AnchorUser).where(model.AnchorUser.customerId == anchor_customer_id)).scalar_one_or_none()
        
        account_number = data.get("included")[0].get("attributes").get("accountNumber")
        bank = data.get("included")[0].get("attributes").get("bank")
        name = data.get("included")[0].get("attributes").get("name")
        bank_code = data.get("included")[0].get("attributes").get("bank").get("code")

        print(account_number, bank, name)

        account_creation = model.AnchorAccount(anchorUserId=user.anchor_user.id, accountNumber=account_number, bank=bank.get("name"), name=name, bankCode=bank_code)
        db.add(account_creation)
        db.commit()
        db.refresh(account_creation)
        # send account creation email to user

        html_content = f"""
        <html>
        <body>
        <p>Hello {user.first_name} {user.last_name},</p>
        <p>Your account number {account_number} has been created successfully.</p>
        <p>Bank: {bank.get("name")}</p>
        <p>Account Name: {name}</p>
        <p>Thank you for using our service.</p>
        </body>
        </html>
        """
        email_request = await sendEmail(email=user.email, subject="Account Creation", data={"htmlContent": html_content})
        return {"message": "Account number created successfully"}

    anchor_customer_id = data.get("data").get("relationships").get("customer").get("data").get("id")

    if event == "customer.created":
        email = data.get("included")[0].get("attributes").get("email")

        user = db.execute(select(model.User).where(model.User.email == email)).scalar_one_or_none()
        if user.anchor_user is None:
            anchor_user = model.AnchorUser(customerId=anchor_customer_id, userId=user.id)
            db.add(anchor_user)
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        kyc_request = await sendTierTwoKycRequest(anchor_customer_id=anchor_customer_id)

        if kyc_request.status_code != 200:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=kyc_request.json())

        return {"message": "Tier 2 KYC request sent successfully"}

        # start anchor kyc 2 task
    else:

        user = db.execute(select(model.User).join(model.AnchorUser).where(model.AnchorUser.customerId == anchor_customer_id)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if event == "customer.identification.approved":
        
            kyc_request = await sendTierThreeKycRequest(anchor_customer_id=anchor_customer_id)

            if kyc_request.status_code != 200:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=kyc_request.json())

            return {"message": "Tier 3 KYC request sent successfully"}

        # start anchor kyc 3 task

        if event == "customer.identification.rejected":
            pass
        # start anchor kyc 3 task

        if event == "customer.identification.error":
            pass
        # start anchor kyc 3 task

    # start anchor kyc 3 task
        if event == "customer.identification.awaitingDocument":
            document_id = data.get("data").get("relationships").get("documents").get("data")[0].get("id")
            id_type = user.kyc.idType

            db.execute(update(model.Kyc).where(model.Kyc.userId == user.id).values(idType=id_type).returning(model.Kyc)).scalar_one_or_none()
            db.commit()
            return {"message": "KYC document type updated successfully"}

        if event == "document.approved":

            # send kyc verification email to user
            html_content = f"""
            <html>
            <body>
            <p>Hello {user.first_name} {user.last_name},</p>
            <p>Your KYC has been verified successfully.</p>
            <p>Thank you for using our service.</p>
            </body>
            </html>
            """
            email_request = await sendEmail(email=user.email, subject="KYC Verification", data={"htmlContent": html_content})

        # create bank account with anchor
            bank_account_request = await createAnchorDepositAccount(anchor_customer_id=anchor_customer_id)
            if bank_account_request.status_code in [200, 201, 202]:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=bank_account_request.text)
    
            db.execute(update(model.Kyc).where(model.Kyc.userId == user.id).values(verified=True, identityVerified=True).returning(model.Kyc)).scalar_one_or_none()
            db.commit()
            return {"message": "Bank account request sent successfully"}

        # send kyc verification email to user

        # start anchor kyc 4 task

        if event == "virtualNuban.opened":
            virtual_nuban_id = data.get("data").get("relationships").get("settlementAccount").get("data").get("id")
            db.execute(update(model.AnchorUser).where(model.AnchorUser.customerId == anchor_customer_id).values(depositAccountId=virtual_nuban_id).returning(model.AnchorUser)).scalar_one_or_none()
            db.commit()
            return {"message": "Anchor account linked successfully"}

        if event == "document.rejected":
            pass
        


