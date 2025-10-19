class SplitCalculator:
    def __init__(self):
        pass
    
    def calculate_splits(self, bill_items, people, assignments, manual_splits=None):
        """
        Calculate how much each person owes based on item assignments
        
        Args:
            bill_items (list): List of items with 'item' and 'amount' keys
            people (list): List of people names
            assignments (dict): Dict mapping item indices to list of people
            manual_splits (dict): Optional manual split overrides
            
        Returns:
            dict: Dictionary mapping person names to amounts owed
        """
        if manual_splits is None:
            manual_splits = {}
        
        # Initialize splits for each person
        splits = {person: 0.0 for person in people}
        
        # Process each item
        for i, item in enumerate(bill_items):
            item_key = f"item_{i}"
            assigned_people = assignments.get(item_key, [])
            
            if not assigned_people:
                continue
            
            amount = float(item['amount'])
            
            # Check if there's a manual split for this item
            if item_key in manual_splits:
                # Use manual split amounts
                manual_amounts = manual_splits[item_key]
                for person, person_amount in manual_amounts.items():
                    if person in splits:
                        splits[person] += float(person_amount)
            else:
                # Equal split among assigned people
                per_person = amount / len(assigned_people)
                for person in assigned_people:
                    if person in splits:
                        splits[person] += per_person
        
        # Round to 2 decimal places
        for person in splits:
            splits[person] = round(splits[person], 2)
        
        return splits
    
    def calculate_with_tax(self, base_splits, tax_amount, tax_type='proportional'):
        """
        Add tax/service charges to the splits
        
        Args:
            base_splits (dict): Base splits without tax
            tax_amount (float): Total tax/service charge amount
            tax_type (str): 'proportional' or 'equal'
            
        Returns:
            dict: Updated splits with tax included
        """
        if tax_amount <= 0:
            return base_splits
        
        total_base = sum(base_splits.values())
        if total_base <= 0:
            return base_splits
        
        updated_splits = base_splits.copy()
        
        if tax_type == 'proportional':
            # Distribute tax proportionally based on each person's share
            for person, amount in base_splits.items():
                if total_base > 0:
                    person_tax = (amount / total_base) * tax_amount
                    updated_splits[person] = round(amount + person_tax, 2)
        
        elif tax_type == 'equal':
            # Split tax equally among all people
            per_person_tax = tax_amount / len(base_splits)
            for person, amount in base_splits.items():
                updated_splits[person] = round(amount + per_person_tax, 2)
        
        return updated_splits
    
    def validate_splits(self, splits, expected_total, tolerance=0.01):
        """
        Validate that splits sum to expected total
        
        Args:
            splits (dict): Calculated splits
            expected_total (float): Expected total amount
            tolerance (float): Acceptable difference
            
        Returns:
            tuple: (is_valid, actual_total, difference)
        """
        actual_total = sum(splits.values())
        difference = abs(actual_total - expected_total)
        is_valid = difference <= tolerance
        
        return is_valid, actual_total, difference
    
    def adjust_splits_for_rounding(self, splits, target_total):
        """
        Adjust splits to match target total, handling rounding discrepancies
        
        Args:
            splits (dict): Current splits
            target_total (float): Target total to match
            
        Returns:
            dict: Adjusted splits
        """
        current_total = sum(splits.values())
        difference = target_total - current_total
        
        if abs(difference) < 0.01:
            return splits
        
        # Find the person with the highest amount to adjust
        adjusted_splits = splits.copy()
        if difference != 0:
            max_person = max(splits, key=splits.get)
            adjusted_splits[max_person] = round(splits[max_person] + difference, 2)
        
        return adjusted_splits
