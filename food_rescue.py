"""A simple terminal program for coordinating possible food donations."""
from abc import ABC, abstractmethod
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d %H:%M"
def get_quantity(prompt):
    try:
        amount = int(input(prompt))
    except ValueError as error:
        raise ValueError("Please enter a whole number.") from error
    if amount <= 0:
        raise ValueError("The quantity must be greater than zero.")
    return amount
def get_date(prompt):
    try:
        return datetime.strptime(input(prompt).strip(), DATE_FORMAT)
    except ValueError as error:
        raise ValueError("Use YYYY-MM-DD HH:MM for the date and time.") from error
def check_name(value, label):
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value
class FoodItem(ABC):
    next_id = 1
    category = "Food"
    def __init__(self, food_name, donor, amount, deadline, eligible, condition):
        self.id = f"F{FoodItem.next_id:03}"
        FoodItem.next_id += 1
        self.name = check_name(food_name, "Food name")
        self.donor = check_name(donor, "Donor name")
        self.total = self.remaining = amount
        self.donated = self.wasted = 0
        self.deadline, self.eligible = deadline, eligible
        self.condition = check_name(condition, "Condition")
        self.status = "Available"
    def _remove_quantity(self, amount, reason):
        if amount <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if amount > self.remaining:
            raise ValueError("That is more than the remaining food quantity.")
        self.remaining -= amount
        if reason == "donated":
            self.donated += amount
        else:
            self.wasted += amount
        if self.remaining == 0:
            self.status = "Complete"
        else:
            self.status = "Partly accounted for"
    def record_donation(self, amount):
        if not self.eligible:
            raise ValueError("This food is marked as ineligible.")
        if datetime.now() > self.deadline:
            raise ValueError("The entered safe-use deadline has passed.")
        self._remove_quantity(amount, "donated")
    def record_waste(self, amount):
        self._remove_quantity(amount, "wasted")
    @abstractmethod
    def calculate_urgency(self):
        raise NotImplementedError
class PreparedMeal(FoodItem):
    category = "Prepared meal"
    def __init__(self, *args, prepared_at):
        super().__init__(*args)
        self.prepared_at = prepared_at
    def calculate_urgency(self):
        hours_left = (self.deadline - datetime.now()).total_seconds() / 3600
        score = 100 - max(0, hours_left) * 8
        return max(0, min(100, score))
class PackagedFood(FoodItem):
    category = "Packaged food"
    def calculate_urgency(self):
        hours_left = (self.deadline - datetime.now()).total_seconds() / 3600
        score = 100 - max(0, hours_left) / 24 * 10
        return max(0, min(100, score))
class FreshProduce(FoodItem):
    category = "Fresh produce"
    def calculate_urgency(self):
        hours_left = (self.deadline - datetime.now()).total_seconds() / 3600
        score = 100 if hours_left <= 0 else 85 - hours_left / 24 * 12
        if "ripe" in self.condition.lower():
            score += 15
        return max(0, min(100, score))
class Donor:
    def __init__(self, donor_name):
        self.name = check_name(donor_name, "Donor name")
class Recipient:
    next_id = 1
    def __init__(self, recipient_name, categories, capacity):
        self.id = f"R{Recipient.next_id:03}"
        Recipient.next_id += 1
        self.name = check_name(recipient_name, "Recipient name")
        self.categories = set(categories)
        self.capacity = capacity
        self.received = 0
    @property
    def available_capacity(self):
        return self.capacity - self.received
class FoodInventory:
    def __init__(self):
        self.items = []
    def find(self, food_id):
        for food in self.items:
            if food.id.lower() == food_id.strip().lower():
                return food
        raise ValueError("Food ID not found.")
    def get_urgent_food(self):
        available_food = [food for food in self.items if food.remaining > 0]
        return sorted(available_food,
                      key=lambda food: food.calculate_urgency(), reverse=True)
class DonationManager:
    def __init__(self, inventory):
        self.inventory = inventory
        self.recipients = []
        self.donations = []
    def find_matches(self, food):
        if not food.eligible or datetime.now() > food.deadline:
            return []
        return [recipient for recipient in self.recipients
                if food.category in recipient.categories
                and recipient.available_capacity > 0 and food.remaining > 0]
    def record_donation(self, food_id, recipient_id, amount):
        food = self.inventory.find(food_id)
        recipient = next((r for r in self.recipients
                          if r.id.lower() == recipient_id.strip().lower()), None)
        if recipient is None:
            raise ValueError("Recipient ID not found.")
        if food.category not in recipient.categories:
            raise ValueError("This recipient does not accept this food category.")
        if amount > recipient.available_capacity:
            raise ValueError("Donation is larger than recipient capacity.")
        food.record_donation(amount)
        recipient.received += amount
        self.donations.append((food.id, recipient.id, amount))
class WasteReport:
    def __init__(self, inventory):
        self.inventory = inventory
    def display(self):
        foods = self.inventory.items
        total = sum(food.total for food in foods)
        donated = sum(food.donated for food in foods)
        wasted = sum(food.wasted for food in foods)
        remaining = sum(food.remaining for food in foods)
        print(f"\nRegistered {total}, donated {donated}, wasted {wasted}, remaining {remaining}")
        print(f"Donation: {donated / total * 100 if total else 0:.1f}% | "
              f"waste: {wasted / total * 100 if total else 0:.1f}%")
        print("\nCategory totals:")
        for category in sorted({food.category for food in foods}):
            group = [food for food in foods if food.category == category]
            print(f"{category}: {sum(f.total for f in group)} registered, "
                  f"{sum(f.donated for f in group)} donated, "
                  f"{sum(f.wasted for f in group)} wasted")
        unresolved = [food for food in foods if food.remaining]
        print("\nUnresolved food:")
        if not unresolved:
            print("None")
        for food in unresolved:
            tag = "urgent" if food.calculate_urgency() >= 70 else "unresolved"
            print(f"{food.id} {food.name}: {food.remaining} left ({tag})")
class FoodRescue:
    def __init__(self):
        self.inventory = FoodInventory()
        self.donation_manager = DonationManager(self.inventory)
        self.report = WasteReport(self.inventory)
    def register_food(self):
        food_types = {"1": PreparedMeal, "2": PackagedFood, "3": FreshProduce}
        print("1. Prepared meal  2. Packaged food  3. Fresh produce")
        food_class = food_types.get(input("Category: ").strip())
        if food_class is None:
            raise ValueError("Choose category 1, 2, or 3.")
        details = (input("Food name: "), input("Donor name: "),
                   get_quantity("Quantity: "),
                   get_date("Safe-use deadline (YYYY-MM-DD HH:MM): "))
        answer = input("Checked as suitable to offer? (y/n): ").strip().lower()
        if answer not in ("y", "yes", "n", "no"):
            raise ValueError("Please answer y or n.")
        details += (answer in ("y", "yes"), input("Condition and storage note: "))
        if food_class == PreparedMeal:
            food = PreparedMeal(*details,
                                prepared_at=get_date("Prepared at (YYYY-MM-DD HH:MM): "))
        else:
            food = food_class(*details)
        self.inventory.items.append(food)
        print(f"Registered {food.id} from {food.donor}.")
    def register_recipient(self):
        category_names = {"1": PreparedMeal.category, "2": PackagedFood.category,
                          "3": FreshProduce.category}
        print("Accepted categories: 1. meal  2. packaged  3. produce")
        choices = input("Enter category numbers separated by commas: ").split(",")
        if not choices or any(choice.strip() not in category_names for choice in choices):
            raise ValueError("Use category numbers 1, 2, or 3.")
        categories = [category_names[choice.strip()] for choice in choices]
        recipient = Recipient(input("Organization or group name: "), categories,
                              get_quantity("Maximum receiving capacity: "))
        self.donation_manager.recipients.append(recipient)
        print(f"Registered recipient {recipient.id}.")
    def show_inventory(self, foods=None):
        foods = self.inventory.items if foods is None else foods
        if not foods:
            print("No food records.")
            return
        for food in foods:
            print(f"{food.id} | {food.name} | {food.category} | "
                  f"{food.remaining}/{food.total} available | "
                  f"{food.deadline.strftime(DATE_FORMAT)} | "
                  f"{food.donor} | {food.status} | eligible: {food.eligible}")
    def show_matches(self):
        food = self.inventory.find(input("Food ID: "))
        matches = self.donation_manager.find_matches(food)
        if not matches:
            print("No eligible recipient matches found.")
            return
        print("Possible matches (delivery is not confirmed):")
        for recipient in matches:
            print(f"{recipient.id} {recipient.name}; "
                  f"capacity left: {recipient.available_capacity}")
    def record_donation(self):
        self.donation_manager.record_donation(
            input("Food ID: "), input("Recipient ID: "),
            get_quantity("Quantity to donate: "))
        print("Donation recorded. Delivery is not independently verified.")
    def record_waste(self):
        food = self.inventory.find(input("Food ID: "))
        amount = get_quantity("Quantity discarded: ")
        food.record_waste(amount)
        print("Waste recorded.")
    def run(self):
        actions = {"1": self.register_food, "2": self.register_recipient,
                   "3": self.show_inventory,
                   "4": lambda: self.show_inventory(self.inventory.get_urgent_food()),
                   "5": self.show_matches, "6": self.record_donation,
                   "7": self.record_waste, "8": self.report.display}
        while True:
            print("\nFoodRescue Menu")
            print("1 Register food | 2 Register recipient | 3 Inventory | 4 Urgent")
            print("5 Find matches | 6 Donation | 7 Waste | 8 Report | 9 Exit")
            choice = input("Choose an option: ").strip()
            if choice == "9":
                print("Goodbye. A deadline alone does not prove food is safe.")
                break
            action = actions.get(choice)
            if action is None:
                print("Choose a number from 1 to 9.")
                continue
            try:
                action()
            except ValueError as error:
                print(f"Input error: {error}")
if __name__ == "__main__":
    FoodRescue().run()
