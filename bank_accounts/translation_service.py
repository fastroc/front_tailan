"""
Mongolian-English Translation Service for Bank Statements
Provides translation mappings with confidence scoring
"""

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MongolianTranslationService:
    """
    Handles translation between Mongolian Cyrillic and English
    with confidence scoring for bank statement processing
    """
    
    # Account Type Translations (High Confidence)
    ACCOUNT_TYPES = {
        'ХАРИЛЦАХ/БАЙГУУЛЛАГА': {
            'english': 'CURRENT/ORGANIZATION', 
            'confidence': 1.0,
            'category': 'current_account'
        },
        'ХАДГАЛАМЖ/ХУВЬ ХҮН': {
            'english': 'SAVINGS/INDIVIDUAL', 
            'confidence': 1.0,
            'category': 'savings_account'
        },
        'ЗЭЭЛ/БАЙГУУЛЛАГА': {
            'english': 'LOAN/ORGANIZATION', 
            'confidence': 1.0,
            'category': 'loan_account'
        },
        'ДЕПОЗИТ/ХУВЬ ХҮН': {
            'english': 'DEPOSIT/INDIVIDUAL', 
            'confidence': 1.0,
            'category': 'deposit_account'
        },
        'ХАРИЛЦАХ/ХУВЬ ХҮН': {
            'english': 'CURRENT/INDIVIDUAL', 
            'confidence': 1.0,
            'category': 'current_account'
        },
    }
    
    # Header Field Translations
    HEADER_FIELDS = {
        'Хэвлэсэн огноо': {
            'english': 'Print Date',
            'confidence': 1.0,
            'field_type': 'date'
        },
        'Депозит дансны дэлгэрэнгүй хуулга': {
            'english': 'Deposit Account Detailed Statement',
            'confidence': 1.0,
            'field_type': 'title'
        },
        'Хэрэглэгч': {
            'english': 'Account Holder',
            'confidence': 1.0,
            'field_type': 'account_holder'
        },
        'Интервал': {
            'english': 'Date Range',
            'confidence': 1.0,
            'field_type': 'date_range'
        },
        'Дансны дугаар': {
            'english': 'Account Number',
            'confidence': 1.0,
            'field_type': 'account_number'
        },
    }
    
    # Transaction Column Headers
    COLUMN_HEADERS = {
        'Огноо': {
            'english': 'Date',
            'confidence': 1.0,
            'column_type': 'date'
        },
        'Гүйлгээний огноо': {
            'english': 'Date',
            'confidence': 1.0,
            'column_type': 'date'
        },
        'Дүн': {
            'english': 'Amount',
            'confidence': 1.0,
            'column_type': 'amount'
        },
        'Дебит гүйлгээ': {
            'english': 'Debit',
            'confidence': 1.0,
            'column_type': 'debit'
        },
        'Кредит гүйлгээ': {
            'english': 'Credit',
            'confidence': 1.0,
            'column_type': 'credit'
        },
        'Тайлбар': {
            'english': 'Description',
            'confidence': 1.0,
            'column_type': 'description'
        },
        'Гүйлгээний утга': {
            'english': 'Description',
            'confidence': 1.0,
            'column_type': 'description'
        },
        'Лавлагаа': {
            'english': 'Reference',
            'confidence': 1.0,
            'column_type': 'reference'
        },
        'Хүлээн авагч': {
            'english': 'Payee',
            'confidence': 1.0,
            'column_type': 'payee'
        },
        'Харьцсан данс': {
            'english': 'Counterpart_Account',
            'confidence': 1.0,
            'column_type': 'account'
        },
        'Салбар': {
            'english': 'Branch',
            'confidence': 1.0,
            'column_type': 'branch'
        },
        'Эхний үлдэгдэл': {
            'english': 'Opening_Balance',
            'confidence': 1.0,
            'column_type': 'balance'
        },
        'Эцсийн үлдэгдэл': {
            'english': 'Closing_Balance',
            'confidence': 1.0,
            'column_type': 'balance'
        },
        'Нийт дүн': {
            'english': 'Total_Amount',
            'confidence': 1.0,
            'column_type': 'summary'
        },
        'Нийт дүн:': {
            'english': 'Total_Amount',
            'confidence': 1.0,
            'column_type': 'summary'
        },
        'Нийт': {
            'english': 'Total',
            'confidence': 1.0,
            'column_type': 'summary'
        },
        'Дүнгийн нийлбэр': {
            'english': 'Sum_Total',
            'confidence': 1.0,
            'column_type': 'summary'
        },
        'Илгээгч': {
            'english': 'Payer',
            'confidence': 1.0,
            'column_type': 'payer'
        },
        'Үлдэгдэл': {
            'english': 'Balance',
            'confidence': 1.0,
            'column_type': 'balance'
        },
        'Орлого': {
            'english': 'Credit',
            'confidence': 1.0,
            'column_type': 'credit'
        },
        'Зарлага': {
            'english': 'Debit',
            'confidence': 1.0,
            'column_type': 'debit'
        },
    }
    
    # Common Transaction Terms
    TRANSACTION_TERMS = {
        'орлого': {'english': 'income', 'confidence': 0.9, 'category': 'credit'},
        'зарлага': {'english': 'expense', 'confidence': 0.9, 'category': 'debit'},
        'шилжүүлэг': {'english': 'transfer', 'confidence': 0.9, 'category': 'transfer'},
        'татварын төлбөр': {'english': 'tax payment', 'confidence': 0.85, 'category': 'tax'},
        'цалин': {'english': 'salary', 'confidence': 0.9, 'category': 'salary'},
        'бонус': {'english': 'bonus', 'confidence': 0.95, 'category': 'bonus'},
        'ажлын хөлс': {'english': 'wages', 'confidence': 0.9, 'category': 'wages'},
        'банкны шимтгэл': {'english': 'bank fee', 'confidence': 0.9, 'category': 'fee'},
        'хүү': {'english': 'interest', 'confidence': 0.9, 'category': 'interest'},
        'зээлийн төлбөр': {'english': 'loan payment', 'confidence': 0.9, 'category': 'loan_payment'},
        'карт': {'english': 'card', 'confidence': 0.8, 'category': 'card_transaction'},
        'ATM': {'english': 'ATM', 'confidence': 1.0, 'category': 'atm'},
        'цахим': {'english': 'online', 'confidence': 0.8, 'category': 'online'},
        'дэлгүүр': {'english': 'store', 'confidence': 0.8, 'category': 'retail'},
        'төлбөр': {'english': 'payment', 'confidence': 0.85, 'category': 'payment'},
        'авлага': {'english': 'receipt', 'confidence': 0.8, 'category': 'receipt'},
    }
    
    # Date format patterns
    DATE_PATTERNS = [
        r'(\d{4})/(\d{1,2})/(\d{1,2})',  # YYYY/MM/DD
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY or DD-MM-YYYY
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # DD.MM.YYYY
    ]
    
    # Amount format patterns
    AMOUNT_PATTERNS = [
        r'([+-]?\d{1,3}(?:,\d{3})*\.?\d*)',  # 1,000.00 or 1,000
        r'([+-]?\d+\.?\d*)',  # Simple decimal
        r'([+-]?\d{1,3}(?:\s\d{3})*\.?\d*)',  # 1 000.00 (space separator)
    ]

    @classmethod
    def translate_text(cls, text: str) -> str:
        """
        General text translation method
        Tries multiple dictionaries to find the best translation
        """
        if not text:
            return ""
        
        # Try column headers first
        header_result = cls.translate_column_header(text)
        if header_result and header_result.get('confidence', 0) > 0.7:
            return header_result.get('english', text)
        
        # Try description translation
        desc_result = cls.translate_description(text)
        if desc_result and desc_result.get('confidence', 0) > 0.7:
            return desc_result.get('english', text)
        
        # Try header field translation
        field_result = cls.translate_header_field(text)
        if field_result and field_result.get('confidence', 0) > 0.7:
            return field_result.get('english', text)
        
        # Return original text if no good translation found
        return text

    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, float]:
        """
        Detect language of text with confidence score
        Returns: (language_code, confidence)
        """
        if not text or not text.strip():
            return 'unknown', 0.0
        
        # Count Cyrillic characters
        cyrillic_chars = len(re.findall(r'[а-яёА-ЯЁ]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        total_letters = cyrillic_chars + latin_chars
        
        if total_letters == 0:
            return 'unknown', 0.0
        
        cyrillic_ratio = cyrillic_chars / total_letters
        
        if cyrillic_ratio > 0.7:
            return 'mn', min(cyrillic_ratio, 1.0)
        elif cyrillic_ratio < 0.3:
            return 'en', min(1.0 - cyrillic_ratio, 1.0)
        else:
            return 'mixed', 0.5 + abs(0.5 - cyrillic_ratio)

    @classmethod
    def translate_account_type(cls, mongolian_text: str) -> Dict:
        """
        Translate Mongolian account type to English
        Returns: {'english': str, 'confidence': float, 'category': str}
        """
        if not mongolian_text:
            return {'english': '', 'confidence': 0.0, 'category': 'unknown'}
        
        # Clean input
        clean_text = mongolian_text.strip()
        
        # Exact match
        if clean_text in cls.ACCOUNT_TYPES:
            return cls.ACCOUNT_TYPES[clean_text]
        
        # Partial match with lower confidence
        for mn_type, translation in cls.ACCOUNT_TYPES.items():
            if mn_type in clean_text or clean_text in mn_type:
                return {
                    'english': translation['english'],
                    'confidence': translation['confidence'] * 0.8,  # Reduced confidence
                    'category': translation['category']
                }
        
        return {'english': clean_text, 'confidence': 0.1, 'category': 'unknown'}

    @classmethod
    def translate_header_field(cls, mongolian_text: str) -> Dict:
        """
        Translate header field name
        Returns: {'english': str, 'confidence': float, 'field_type': str}
        """
        if not mongolian_text:
            return {'english': '', 'confidence': 0.0, 'field_type': 'unknown'}
        
        clean_text = mongolian_text.strip()
        
        # Exact match
        if clean_text in cls.HEADER_FIELDS:
            return cls.HEADER_FIELDS[clean_text]
        
        # Partial match
        for mn_field, translation in cls.HEADER_FIELDS.items():
            if mn_field in clean_text or clean_text in mn_field:
                return {
                    'english': translation['english'],
                    'confidence': translation['confidence'] * 0.7,
                    'field_type': translation['field_type']
                }
        
        return {'english': clean_text, 'confidence': 0.1, 'field_type': 'unknown'}

    @classmethod
    def translate_column_header(cls, header_text: str) -> Dict:
        """
        Translate column header with confidence
        Returns: {'english': str, 'confidence': float, 'column_type': str}
        """
        if not header_text:
            return {'english': '', 'confidence': 0.0, 'column_type': 'unknown'}
        
        clean_text = header_text.strip()
        clean_text_lower = clean_text.lower()
        
        # Check exact matches (case-insensitive)
        for mn_header, translation in cls.COLUMN_HEADERS.items():
            if mn_header.lower() == clean_text_lower:
                return translation
        
        # Check partial matches
        for mn_header, translation in cls.COLUMN_HEADERS.items():
            if mn_header.lower() in clean_text_lower or clean_text_lower in mn_header.lower():
                return {
                    'english': translation['english'],
                    'confidence': translation['confidence'] * 0.8,
                    'column_type': translation['column_type']
                }
        
        # Check if it's already English
        english_headers = ['date', 'amount', 'description', 'reference', 'payee', 'balance']
        if clean_text.lower() in english_headers:
            return {
                'english': clean_text.title(),
                'confidence': 0.9,
                'column_type': clean_text.lower()
            }
        
        return {'english': clean_text, 'confidence': 0.2, 'column_type': 'unknown'}

    @classmethod
    def translate_description(cls, description: str) -> Dict:
        """
        Translate transaction description
        Returns: {'english': str, 'confidence': float, 'terms_found': List[Dict]}
        """
        if not description:
            return {'english': '', 'confidence': 0.0, 'terms_found': []}
        
        original_desc = description.strip()
        english_desc = original_desc
        terms_found = []
        total_confidence = 0.0
        
        # Find and translate known terms
        for mn_term, translation in cls.TRANSACTION_TERMS.items():
            if mn_term in original_desc.lower():
                english_desc = english_desc.replace(mn_term, translation['english'])
                terms_found.append({
                    'mongolian': mn_term,
                    'english': translation['english'],
                    'confidence': translation['confidence'],
                    'category': translation['category']
                })
                total_confidence += translation['confidence']
        
        # Calculate overall confidence
        if terms_found:
            avg_confidence = total_confidence / len(terms_found)
        else:
            # Check if it's already mostly English
            lang, lang_confidence = cls.detect_language(original_desc)
            if lang == 'en':
                avg_confidence = lang_confidence
                english_desc = original_desc
            else:
                avg_confidence = 0.3  # Unknown terms get low confidence
        
        return {
            'english': english_desc,
            'confidence': min(avg_confidence, 1.0),
            'terms_found': terms_found
        }

    @classmethod
    def parse_date(cls, date_text: str) -> Tuple[Optional[datetime], float]:
        """
        Parse date from various formats
        Returns: (datetime_object, confidence)
        """
        if not date_text:
            return None, 0.0
        
        clean_date = date_text.strip()
        
        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, clean_date)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Try different date interpretations
                        formats_to_try = []
                        
                        # If first group is 4 digits, it's likely YYYY
                        if len(groups[0]) == 4:
                            formats_to_try.append((int(groups[0]), int(groups[1]), int(groups[2])))  # YYYY, MM, DD
                        else:
                            # Try both MM/DD/YYYY and DD/MM/YYYY
                            if int(groups[1]) <= 12 and int(groups[0]) <= 31:
                                formats_to_try.append((int(groups[2]), int(groups[1]), int(groups[0])))  # YYYY, MM, DD
                            if int(groups[0]) <= 12 and int(groups[1]) <= 31:
                                formats_to_try.append((int(groups[2]), int(groups[0]), int(groups[1])))  # YYYY, MM, DD
                        
                        for year, month, day in formats_to_try:
                            try:
                                parsed_date = datetime(year, month, day)
                                # Higher confidence for more recent dates
                                current_year = datetime.now().year
                                if abs(year - current_year) <= 5:
                                    confidence = 0.9
                                elif abs(year - current_year) <= 10:
                                    confidence = 0.8
                                else:
                                    confidence = 0.6
                                
                                return parsed_date, confidence
                            except ValueError:
                                continue
                                
                except (ValueError, IndexError):
                    continue
        
        return None, 0.0

    @classmethod
    def parse_amount(cls, amount_text: str) -> Tuple[Optional[Decimal], float]:
        """
        Parse amount from various formats
        Returns: (decimal_amount, confidence)
        """
        if not amount_text:
            return None, 0.0
        
        clean_amount = amount_text.strip().replace('₮', '').replace('$', '').replace('¥', '')
        
        for pattern in cls.AMOUNT_PATTERNS:
            match = re.search(pattern, clean_amount)
            if match:
                try:
                    amount_str = match.group(1)
                    # Remove separators and convert
                    amount_str = amount_str.replace(',', '').replace(' ', '')
                    amount = Decimal(amount_str)
                    
                    # Higher confidence for reasonable amounts
                    if 0 < abs(amount) < 1000000000:  # Less than 1 billion
                        confidence = 0.9
                    elif abs(amount) < 10000000000:  # Less than 10 billion
                        confidence = 0.7
                    else:
                        confidence = 0.5
                    
                    return amount, confidence
                except (ValueError, InvalidOperation):
                    continue
        
        return None, 0.0

    @classmethod
    def get_processing_summary(cls, text_data: Dict) -> Dict:
        """
        Get overall processing summary with confidence scores
        """
        summary = {
            'total_fields': 0,
            'successfully_translated': 0,
            'high_confidence_fields': 0,
            'medium_confidence_fields': 0,
            'low_confidence_fields': 0,
            'overall_confidence': 0.0,
            'language_detected': 'unknown',
            'recommendations': []
        }
        
        # This would be implemented based on processing results
        # For now, return template structure
        
        return summary
