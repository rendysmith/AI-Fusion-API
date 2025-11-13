from app.database.billing_models import Product
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.subscription_repository import SubscriptionRepository


class BillingService:
    def __init__(
            self,
            user_repo: UserRepository,
            sub_repo: SubscriptionRepository
    ):
        self.user_repo = user_repo
        self.sub_repo = sub_repo

    async def grant_product_rewards(self, user_id: int, product: Product):

        rewards = product.rewards

        if "credits" in rewards:
            amount = int(rewards["credits"])
            await self.user_repo.add_credits(user_id, amount)


        if "plan_id" in rewards:
            plan_id = int(rewards["plan_id"])
            await self.sub_repo.activate_subscription(user_id, plan_id)
