#!/usr/bin/env python3
"""
Configuration module for Instagram Post Planner

This module defines the PlanConfig dataclass and related utilities
for managing planner configuration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json


@dataclass
class PreferredFirstProduct:
    """Represents a preferred first product with optional day/time constraints"""
    kisakodrenk: str
    gun: Optional[str] = None  # Day name (e.g., "Pazartesi")
    time: Optional[str] = None  # Time (e.g., "09:00")
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "kisakodrenk": self.kisakodrenk,
            "gun": self.gun,
            "time": self.time
        }
    
    @classmethod
    def from_dict(cls, d: dict):
        """Create from dictionary"""
        return cls(
            kisakodrenk=d.get("kisakodrenk", ""),
            gun=d.get("gun"),
            time=d.get("time")
        )


@dataclass
class PlanConfig:
    """Configuration for Instagram Post Planner"""
    
    # Basic plan settings
    stock_excel_path: str = ""
    plan_start_day_name: str = "Pazartesi"
    plan_num_days: int = 7
    
    # Front (FIRST) product settings
    use_yazlik_front: bool = True
    use_kislik_front: bool = True
    allowed_cekim_front: List[str] = field(default_factory=lambda: ["EVET", "NA"])
    one_atilma_allow_na: bool = False
    prioritize_never_used_first: bool = False
    one_atilma_reference_date: str = ""
    one_atilma_min_days: int = 0
    min_total_stock_front: int = 0
    min_nos_front: int = 0
    min_dvm_front: int = 0
    front_size_stock_rules: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    
    # Back product settings
    use_yazlik_back: bool = True
    use_kislik_back: bool = True
    allowed_cekim_back: List[str] = field(default_factory=lambda: ["EVET", "NA"])
    min_total_stock_back: int = 0
    back_size_stock_rules: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    
    # Advanced constraints
    max_same_uruncinsi_in_a_row_per_day: int = 0
    min_distinct_uruncinsi_per_day: int = 0
    max_same_color_in_a_row_per_day: int = 0
    min_distinct_color_per_day: int = 0
    same_kisakod_min_gap_days: int = 0
    max_black_first_per_day: int = 0
    max_first_uses_per_kisakod: int = 0
    max_distinct_kisakod_repeatable: int = 0
    
    # Global stock targets (deprecated, kept for compatibility)
    global_min_first_stock_sum: int = 0
    global_min_total_stock_sum: int = 0
    
    # Prioritization
    prioritize_by_newness: bool = False
    prioritize_by_stock: bool = False
    
    # Preferred products
    preferred_first_products: List[PreferredFirstProduct] = field(default_factory=list)
    preferred_products_in_pool: List[str] = field(default_factory=list)
    forced_preferred_products: List[str] = field(default_factory=list)
    
    # Posting times (from DEFAULT_CFG)
    weekday_times: List[str] = field(default_factory=lambda: [
        "09:00", "10:30", "11:30", "12:30", "13:30", "14:30",
        "15:30", "16:30", "17:30", "19:30", "21:00", "22:30",
    ])
    weekend_times: List[str] = field(default_factory=lambda: [
        "11:00", "12:00", "13:00", "14:00", "15:00",
        "16:00", "17:00", "18:30", "19:30", "21:00",
    ])
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not self.stock_excel_path:
            errors.append("Excel dosya yolu belirtilmelidir")
        
        if self.plan_num_days < 1 or self.plan_num_days > 7:
            errors.append("Plan gün sayısı 1-7 arasında olmalıdır")
        
        valid_days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        if self.plan_start_day_name not in valid_days:
            errors.append(f"Başlangıç günü geçerli bir gün olmalıdır: {', '.join(valid_days)}")
        
        if not self.use_yazlik_front and not self.use_kislik_front:
            errors.append("En az bir front sezon seçilmelidir (Yazlık veya Kışlık)")
        
        if not self.use_yazlik_back and not self.use_kislik_back:
            errors.append("En az bir back sezon seçilmelidir (Yazlık veya Kışlık)")
        
        return errors
    
    def validate_preferred_products_advanced(self, calendar: List[Dict]) -> List[str]:
        """Validate preferred products against calendar"""
        errors = []
        
        if not calendar:
            return errors
        
        # Get all valid day names and times from calendar
        valid_days = set()
        valid_times = set()
        for post in calendar:
            day = post.get("day_name")
            time = post.get("time")
            if day:
                valid_days.add(day)
            if time:
                valid_times.add(time)
        
        for pref in self.preferred_first_products:
            if pref.gun and pref.gun not in valid_days:
                errors.append(f"Tercihli ürün {pref.kisakodrenk} için geçersiz gün: {pref.gun}")
            if pref.time and pref.time not in valid_times:
                errors.append(f"Tercihli ürün {pref.kisakodrenk} için geçersiz saat: {pref.time}")
        
        return errors
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        # Convert front_size_stock_rules from dict to list format
        # Dictionary format: {1: (y, z), 2: (y, z), ...} where y=required_size_count, z=min_sizes_with_stock
        # List format expected: [(required_size_count, min_sizes_with_stock, min_stock_value), ...]
        front_rules_list = []
        for size_count, (min_sizes, min_stock) in self.front_size_stock_rules.items():
            if min_sizes > 0 or min_stock > 0:  # Only include non-zero rules
                front_rules_list.append((size_count, min_sizes, min_stock))
        # Sort by size_count for consistency
        front_rules_list.sort(key=lambda x: x[0])
        
        back_rules_list = []
        for size_count, (min_sizes, min_stock) in self.back_size_stock_rules.items():
            if min_sizes > 0 or min_stock > 0:  # Only include non-zero rules
                back_rules_list.append((size_count, min_sizes, min_stock))
        back_rules_list.sort(key=lambda x: x[0])
        
        return {
            "stock_excel_path": self.stock_excel_path,
            "plan_start_day_name": self.plan_start_day_name,
            "plan_num_days": self.plan_num_days,
            "use_yazlik_front": self.use_yazlik_front,
            "use_kislik_front": self.use_kislik_front,
            "allowed_cekim_front": self.allowed_cekim_front,
            "one_atilma_allow_na": self.one_atilma_allow_na,
            "prioritize_never_used_first": self.prioritize_never_used_first,
            "one_atilma_reference_date": self.one_atilma_reference_date,
            "one_atilma_min_days": self.one_atilma_min_days,
            "min_total_stock_front": self.min_total_stock_front,
            "min_nos_front": self.min_nos_front,
            "min_dvm_front": self.min_dvm_front,
            "front_size_stock_rules": front_rules_list if front_rules_list else [],
            "use_yazlik_back": self.use_yazlik_back,
            "use_kislik_back": self.use_kislik_back,
            "allowed_cekim_back": self.allowed_cekim_back,
            "min_total_stock_back": self.min_total_stock_back,
            "back_size_stock_rules": back_rules_list if back_rules_list else [],
            "max_same_uruncinsi_in_a_row_per_day": self.max_same_uruncinsi_in_a_row_per_day,
            "min_distinct_uruncinsi_per_day": self.min_distinct_uruncinsi_per_day,
            "max_same_color_in_a_row_per_day": self.max_same_color_in_a_row_per_day,
            "min_distinct_color_per_day": self.min_distinct_color_per_day,
            "same_kisakod_min_gap_days": self.same_kisakod_min_gap_days,
            "max_black_first_per_day": self.max_black_first_per_day,
            "max_first_uses_per_kisakod": self.max_first_uses_per_kisakod,
            "max_distinct_kisakod_repeatable": self.max_distinct_kisakod_repeatable,
            "global_min_first_stock_sum": self.global_min_first_stock_sum,
            "global_min_total_stock_sum": self.global_min_total_stock_sum,
            "prioritize_by_newness": self.prioritize_by_newness,
            "prioritize_by_stock": self.prioritize_by_stock,
            "preferred_first_products": [p.to_dict() for p in self.preferred_first_products],
            "preferred_products_in_pool": self.preferred_products_in_pool,
            "forced_preferred_products": self.forced_preferred_products,
            "weekday_times": self.weekday_times,
            "weekend_times": self.weekend_times,
        }
    
    @classmethod
    def from_dict(cls, d: dict):
        """Create configuration from dictionary"""
        # Convert front_size_stock_rules and back_size_stock_rules from list to dict[int, tuple]
        # List format: [(required_size_count, min_sizes_with_stock, min_stock_value), ...]
        # Dict format: {required_size_count: (min_sizes_with_stock, min_stock_value), ...}
        front_rules = {}
        if "front_size_stock_rules" in d:
            rules_data = d["front_size_stock_rules"]
            if isinstance(rules_data, list):
                # List format: [(size_count, min_sizes, min_stock), ...]
                for rule in rules_data:
                    if len(rule) >= 3:
                        size_count, min_sizes, min_stock = rule[0], rule[1], rule[2]
                        front_rules[size_count] = (min_sizes, min_stock)
            elif isinstance(rules_data, dict):
                # Dict format: {str(k): [min_sizes, min_stock], ...}
                for k, v in rules_data.items():
                    front_rules[int(k)] = tuple(v) if isinstance(v, list) else v
        
        back_rules = {}
        if "back_size_stock_rules" in d:
            rules_data = d["back_size_stock_rules"]
            if isinstance(rules_data, list):
                # List format: [(size_count, min_sizes, min_stock), ...]
                for rule in rules_data:
                    if len(rule) >= 3:
                        size_count, min_sizes, min_stock = rule[0], rule[1], rule[2]
                        back_rules[size_count] = (min_sizes, min_stock)
            elif isinstance(rules_data, dict):
                # Dict format: {str(k): [min_sizes, min_stock], ...}
                for k, v in rules_data.items():
                    back_rules[int(k)] = tuple(v) if isinstance(v, list) else v
        
        # Convert preferred_first_products
        preferred = []
        if "preferred_first_products" in d:
            for p in d["preferred_first_products"]:
                preferred.append(PreferredFirstProduct.from_dict(p))
        
        return cls(
            stock_excel_path=d.get("stock_excel_path", ""),
            plan_start_day_name=d.get("plan_start_day_name", "Pazartesi"),
            plan_num_days=d.get("plan_num_days", 7),
            use_yazlik_front=d.get("use_yazlik_front", True),
            use_kislik_front=d.get("use_kislik_front", True),
            allowed_cekim_front=d.get("allowed_cekim_front", ["EVET", "NA"]),
            one_atilma_allow_na=d.get("one_atilma_allow_na", False),
            prioritize_never_used_first=d.get("prioritize_never_used_first", False),
            one_atilma_reference_date=d.get("one_atilma_reference_date", ""),
            one_atilma_min_days=d.get("one_atilma_min_days", 0),
            min_total_stock_front=d.get("min_total_stock_front", 0),
            min_nos_front=d.get("min_nos_front", 0),
            min_dvm_front=d.get("min_dvm_front", 0),
            front_size_stock_rules=front_rules,
            use_yazlik_back=d.get("use_yazlik_back", True),
            use_kislik_back=d.get("use_kislik_back", True),
            allowed_cekim_back=d.get("allowed_cekim_back", ["EVET", "NA"]),
            min_total_stock_back=d.get("min_total_stock_back", 0),
            back_size_stock_rules=back_rules,
            max_same_uruncinsi_in_a_row_per_day=d.get("max_same_uruncinsi_in_a_row_per_day", 0),
            min_distinct_uruncinsi_per_day=d.get("min_distinct_uruncinsi_per_day", 0),
            max_same_color_in_a_row_per_day=d.get("max_same_color_in_a_row_per_day", 0),
            min_distinct_color_per_day=d.get("min_distinct_color_per_day", 0),
            same_kisakod_min_gap_days=d.get("same_kisakod_min_gap_days", 0),
            max_black_first_per_day=d.get("max_black_first_per_day", 0),
            max_first_uses_per_kisakod=d.get("max_first_uses_per_kisakod", 0),
            max_distinct_kisakod_repeatable=d.get("max_distinct_kisakod_repeatable", 0),
            global_min_first_stock_sum=d.get("global_min_first_stock_sum", 0),
            global_min_total_stock_sum=d.get("global_min_total_stock_sum", 0),
            prioritize_by_newness=d.get("prioritize_by_newness", False),
            prioritize_by_stock=d.get("prioritize_by_stock", False),
            preferred_first_products=preferred,
            preferred_products_in_pool=d.get("preferred_products_in_pool", []),
            forced_preferred_products=d.get("forced_preferred_products", []),
            weekday_times=d.get("weekday_times", [
                "09:00", "10:30", "11:30", "12:30", "13:30", "14:30",
                "15:30", "16:30", "17:30", "19:30", "21:00", "22:30",
            ]),
            weekend_times=d.get("weekend_times", [
                "11:00", "12:00", "13:00", "14:00", "15:00",
                "16:00", "17:00", "18:30", "19:30", "21:00",
            ]),
        )


def create_default_config() -> PlanConfig:
    """Create a default PlanConfig instance"""
    return PlanConfig()

