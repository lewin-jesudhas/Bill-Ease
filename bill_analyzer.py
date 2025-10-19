import os
import json
from openai import OpenAI
import streamlit as st

class BillAnalyzer:
    def __init__(self):
        # Get API key from environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.client = OpenAI(api_key=api_key)
    
    def extract_items(self, image_base64):
        """
        Extract items and prices from a bill image using GPT Vision
        
        Args:
            image_base64 (str): Base64 encoded image string
            
        Returns:
            list: List of dictionaries with 'item' and 'amount' keys
        """
        try:
            # Create the prompt for bill analysis
            system_prompt = """
            You are BillEase, an expert bill analyzer. Your task is to extract item names and prices from restaurant/café bills.
            
            Instructions:
            1. Identify ALL food and beverage items with their prices
            2. Ignore: headers, restaurant info, taxes, service charges, totals, thank you notes
            3. Clean up OCR mistakes (e.g., "Bulter Nan" → "Butter Naan")
            4. Ensure all prices are numbers (remove currency symbols)
            5. If quantity is mentioned, extract individual item price
            
            Return ONLY a JSON array in this exact format:
            [
                {"item": "Item Name", "amount": price_as_number},
                {"item": "Another Item", "amount": price_as_number}
            ]
            
            Example output:
            [
                {"item": "Paneer Butter Masala", "amount": 180},
                {"item": "Butter Naan", "amount": 40},
                {"item": "Sweet Lassi", "amount": 60}
            ]
            """
            
            user_prompt = """
            Please analyze this restaurant bill image and extract all food/beverage items with their prices. 
            Return the results as a JSON array with 'item' and 'amount' fields.
            """
            
            # Make API call to GPT Vision
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=2048
            )
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Debug logging
            print(f"[DEBUG] API Response content: {content}")
            
            # Check if content is empty
            if not content or content.strip() == "":
                st.error("Received empty response from AI. Please try again.")
                return []
            
            # Try to extract JSON array from the response
            try:
                # First try to parse as direct JSON
                result = json.loads(content)
                
                # If it's an object with an array inside, extract the array
                if isinstance(result, dict):
                    if 'items' in result:
                        items = result['items']
                    elif 'bill_items' in result:
                        items = result['bill_items']
                    elif 'extracted_items' in result:
                        items = result['extracted_items']
                    else:
                        # Look for the first array in the object
                        for key, value in result.items():
                            if isinstance(value, list):
                                items = value
                                break
                        else:
                            items = []
                else:
                    items = result
                
                # Validate and clean the items
                cleaned_items = []
                for item in items:
                    if isinstance(item, dict) and 'item' in item and 'amount' in item:
                        try:
                            # Clean up the item name
                            item_name = str(item['item']).strip()
                            # Convert amount to float
                            amount = float(item['amount'])
                            
                            if item_name and amount > 0:
                                cleaned_items.append({
                                    'item': item_name,
                                    'amount': amount
                                })
                        except (ValueError, TypeError):
                            continue
                
                return cleaned_items
                
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse JSON response: {e}")
                st.error(f"Response content: {content}")
                return []
        
        except Exception as e:
            st.error(f"Error during bill analysis: {str(e)}")
            return []
    
    def validate_items(self, items):
        """
        Validate extracted items for completeness and accuracy
        
        Args:
            items (list): List of item dictionaries
            
        Returns:
            tuple: (is_valid, warnings)
        """
        warnings = []
        
        if not items:
            return False, ["No items were extracted from the bill"]
        
        total_amount = 0
        for item in items:
            if not item.get('item') or not item.get('amount'):
                warnings.append(f"Incomplete item found: {item}")
                continue
            
            try:
                amount = float(item['amount'])
                if amount <= 0:
                    warnings.append(f"Invalid amount for {item['item']}: {amount}")
                else:
                    total_amount += amount
            except (ValueError, TypeError):
                warnings.append(f"Invalid amount format for {item['item']}: {item['amount']}")
        
        if total_amount == 0:
            warnings.append("Total amount is zero - this seems incorrect")
        
        return len(warnings) == 0, warnings
