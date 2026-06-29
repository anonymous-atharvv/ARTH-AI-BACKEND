import re

class LanguageService:
    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detects if user is using Hindi (Devanagari script) or Hinglish/English.
        Returns 'hi' or 'en'.
        """
        if not text:
            return "en"
            
        # Check for Devanagari Unicode block (U+0900 to U+097F)
        if re.search(r"[\u0900-\u097f]", text):
            return "hi"
            
        # Basic vocabulary list of common Hindi words written in Roman script (Hinglish)
        hinglish_words = {
            "mera", "hai", "ka", "ki", "ko", "se", "aur", "ek", "do", "tin", 
            "aaj", "kal", "diya", "mili", "rupaye", "rs", "hona", "hua", "huin",
            "kharch", "kamai", "faida", "nuksan", "hisab", "kitab", "bhejo", 
            "banao", "karo", "naam", "auto", "kirana", "rupay", "doot", "namaste"
        }
        
        words = set(re.findall(r"\b\w+\b", text.lower()))
        if words.intersection(hinglish_words):
            return "hi"
            
        return "en"

    @staticmethod
    def translate_category(category_code: str, target_lang: str) -> str:
        """Translate system category code into target language representation"""
        category_names_hi = {
            "transport_fuel": "ईंधन/यातायात",
            "inventory": "माल/स्टॉक",
            "labor_wages": "मजदूरी",
            "sales_service": "सेवा आय",
            "sales_product": "बिक्री",
            "food_personal": "खाना/व्यक्तिगत",
            "mobile_internet": "मोबाइल/इंटरनेट",
            "utilities": "बिजली/पानी",
            "equipment": "उपकरण",
            "rent_premises": "किराया",
            "other_expense": "अन्य खर्च",
            "other_income": "अन्य आय",
        }
        category_names_en = {
            "transport_fuel": "Fuel/Transport",
            "inventory": "Stock Purchase",
            "labor_wages": "Wages/Labor",
            "sales_service": "Service Income",
            "sales_product": "Sales/Product",
            "food_personal": "Food/Personal",
            "mobile_internet": "Mobile/Internet",
            "utilities": "Utilities",
            "equipment": "Equipment",
            "rent_premises": "Rent",
            "other_expense": "Other Expense",
            "other_income": "Other Income",
        }
        
        if target_lang == "hi":
            return category_names_hi.get(category_code, category_code)
        return category_names_en.get(category_code, category_code.replace("_", " ").title())
