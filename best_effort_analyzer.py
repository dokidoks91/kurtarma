#!/usr/bin/env python3
"""
Best Effort Analyzer Module for Instagram Post Planner

This module analyzes constraints when they cannot be met and suggests
relaxations to help the user understand what adjustments might help.
"""

from typing import List, Dict, Any, Optional
import pandas as pd


class BestEffortAnalyzer:
    """Analyzes constraints and suggests relaxations for best-effort planning"""
    
    def __init__(self, calendar: List[Dict], unique_products: pd.DataFrame, cfg: Dict, raw_df: Optional[pd.DataFrame] = None):
        """
        Initialize analyzer with planning context.
        
        Args:
            calendar: List of post slots
            unique_products: All unique products before filtering
            cfg: Configuration dictionary
            raw_df: Raw stock data DataFrame (optional)
        """
        self.calendar = calendar
        self.unique_products = unique_products
        self.cfg = cfg
        self.raw_df = raw_df
    
    def analyze_and_suggest_relaxations(self, posts: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Analyze constraints and suggest relaxations.
        
        Args:
            posts: Optional list of trial posts for assignment-based analysis
            
        Returns:
            Dictionary with:
            - suggestions: List of relaxation suggestions
            - soft_violations: List of soft constraint violations
            - hard_violations: List of hard constraint violations
            - diagnostics: Diagnostic information
            - message: Formatted message
        """
        suggestions = []
        
        # Analyze basic constraints (pool-based)
        suggestions.extend(self._analyze_first_min_stock())
        suggestions.extend(self._analyze_back_min_stock())
        suggestions.extend(self._analyze_first_size_stock_rules())
        suggestions.extend(self._analyze_back_size_stock_rules())
        suggestions.extend(self._analyze_one_atilma_constraint())  # One Atilma Tarihi relaxation
        suggestions.extend(self._analyze_advanced_first_constraints(posts=posts))
        suggestions.extend(self._analyze_per_day_constraints(posts=posts))
        suggestions.extend(self._analyze_global_stock_targets_standalone())
        
        # If posts are available, analyze assignment-based constraints
        if posts:
            suggestions.extend(self._analyze_global_stock_targets(posts))
        
        # Calculate diagnostics
        from instagram_auto_post import filter_first_products, filter_back_products
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        first_pool = filter_first_products(self.unique_products, cfg_with_calendar)
        back_pool = filter_back_products(self.unique_products, cfg_with_calendar)
        
        required_first = len(self.calendar)
        required_back = len(self.calendar) * 9
        
        diagnostics = {
            "first_pool_size": len(first_pool),
            "back_pool_size": len(back_pool),
            "required_first": required_first,
            "required_back": required_back,
        }
        
        return {
            "suggestions": suggestions,
            "soft_violations": [],
            "hard_violations": [],
            "diagnostics": diagnostics,
            "message": "Relaxation suggestions generated",
        }
    
    def _analyze_first_min_stock(self) -> List[Dict]:
        """Analyze FIRST minimum stock constraint and suggest relaxation"""
        suggestions = []
        min_stock = self.cfg.get("min_total_stock_front", 0)
        if min_stock == 0:
            return suggestions
        
        from instagram_auto_post import filter_first_products
        
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        
        # Get current pool
        current_pool = filter_first_products(self.unique_products, cfg_with_calendar)
        
        # Try more aggressive relaxation values to ensure pool is filled
        # Try: -1, -2, -3, -5, -10, -15, -20, -25, -50, -75, -100, or down to 0
        relaxation_steps = [1, 2, 3, 5, 10, 15, 20, 25, 50, 75, 100]
        best_suggestion = None
        max_additional = 0
        
        for step in relaxation_steps:
            new_threshold = max(0, min_stock - step)
            if new_threshold >= min_stock:
                continue
            
            test_cfg = self.cfg.copy()
            test_cfg["min_total_stock_front"] = new_threshold
            test_cfg["_calendar_for_pool"] = self.calendar
            
            test_pool = filter_first_products(self.unique_products, test_cfg)
            additional = len(test_pool) - len(current_pool)
            
            if additional > max_additional:
                max_additional = additional
                best_suggestion = {
                "rule_name": "FIRST Minimum Toplam Stok",
                "original_value": min_stock,
                "suggested_value": new_threshold,
                "estimated_new_candidates": additional,
                    "rule_type": "FIRST_stock",
                }
        
        # Also try setting to 0 (most aggressive)
        if min_stock > 0:
            test_cfg = self.cfg.copy()
            test_cfg["min_total_stock_front"] = 0
            test_cfg["_calendar_for_pool"] = self.calendar
            test_pool = filter_first_products(self.unique_products, test_cfg)
            additional = len(test_pool) - len(current_pool)
            if additional > max_additional:
                max_additional = additional
                best_suggestion = {
                    "rule_name": "FIRST Minimum Toplam Stok",
                    "original_value": min_stock,
                    "suggested_value": 0,
                    "estimated_new_candidates": additional,
                    "rule_type": "FIRST_stock",
                }
        
        if best_suggestion:
            suggestions.append(best_suggestion)
        
        return suggestions
    
    def _analyze_back_min_stock(self) -> List[Dict]:
        """Analyze BACK minimum stock constraint and suggest relaxation"""
        suggestions = []
        min_stock = self.cfg.get("min_total_stock_back", 0)
        if min_stock == 0:
            return suggestions
        
        from instagram_auto_post import filter_back_products
        
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        
        # Get current pool
        current_pool = filter_back_products(self.unique_products, cfg_with_calendar)
        
        # Try more aggressive relaxation values to ensure pool is filled
        # Try: -1, -2, -3, -5, -10, -15, -20, -25, -50, -75, -100, or down to 0
        relaxation_steps = [1, 2, 3, 5, 10, 15, 20, 25, 50, 75, 100]
        best_suggestion = None
        max_additional = 0
        
        for step in relaxation_steps:
            new_threshold = max(0, min_stock - step)
            if new_threshold >= min_stock:
                continue
            
            test_cfg = self.cfg.copy()
            test_cfg["min_total_stock_back"] = new_threshold
            test_cfg["_calendar_for_pool"] = self.calendar
            
            test_pool = filter_back_products(self.unique_products, test_cfg)
            additional = len(test_pool) - len(current_pool)
            
            if additional > max_additional:
                max_additional = additional
                best_suggestion = {
                "rule_name": "BACK Minimum Toplam Stok",
                "original_value": min_stock,
                "suggested_value": new_threshold,
                "estimated_new_candidates": additional,
                    "rule_type": "BACK_stock",
                }
        
        # Also try setting to 0 (most aggressive)
        if min_stock > 0:
            test_cfg = self.cfg.copy()
            test_cfg["min_total_stock_back"] = 0
            test_cfg["_calendar_for_pool"] = self.calendar
            test_pool = filter_back_products(self.unique_products, test_cfg)
            additional = len(test_pool) - len(current_pool)
            if additional > max_additional:
                max_additional = additional
                best_suggestion = {
                    "rule_name": "BACK Minimum Toplam Stok",
                    "original_value": min_stock,
                    "suggested_value": 0,
                    "estimated_new_candidates": additional,
                    "rule_type": "BACK_stock",
                }
        
        if best_suggestion:
            suggestions.append(best_suggestion)
        
        return suggestions
    
    def _analyze_first_size_stock_rules(self) -> List[Dict]:
        """Analyze FIRST size/stock rules and suggest relaxation"""
        suggestions = []
        rules = self.cfg.get("front_size_stock_rules", [])
        if not rules:
            return suggestions
        
        from instagram_auto_post import filter_first_products
        
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        
        # Get current pool
        current_pool = filter_first_products(self.unique_products, cfg_with_calendar)
        
        # Try relaxing each rule
        for i, rule in enumerate(rules):
            if len(rule) < 3:
                continue
            min_beden, min_stok_per_beden = rule[1], rule[2]
            
            # Try more aggressive relaxation: reduce min_stok_per_beden down to 0
            best_suggestion = None
            max_additional = 0
            
            for step in [1, 2, 3, 5, 10]:
                new_stok = max(0, min_stok_per_beden - step)
                if new_stok >= min_stok_per_beden:
                    continue
                
                new_rules = rules.copy()
                new_rules[i] = (rule[0], min_beden, new_stok)
                
                test_cfg = self.cfg.copy()
                test_cfg["front_size_stock_rules"] = new_rules
                test_cfg["_calendar_for_pool"] = self.calendar
                
                test_pool = filter_first_products(self.unique_products, test_cfg)
                additional = len(test_pool) - len(current_pool)
                
                if additional > max_additional:
                    max_additional = additional
                    best_suggestion = {
                        "rule_name": f"FIRST Beden/Stok Kuralı (Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden)",
                        "original_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={min_stok_per_beden}",
                        "suggested_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={new_stok}",
                        "estimated_new_candidates": additional,
                        "rule_type": "FIRST_size_stock",
                    }
            
            # Also try setting to 0
            if min_stok_per_beden > 0:
                new_rules = rules.copy()
                new_rules[i] = (rule[0], min_beden, 0)
                test_cfg = self.cfg.copy()
                test_cfg["front_size_stock_rules"] = new_rules
                test_cfg["_calendar_for_pool"] = self.calendar
                test_pool = filter_first_products(self.unique_products, test_cfg)
                additional = len(test_pool) - len(current_pool)
                if additional > max_additional:
                    max_additional = additional
                    best_suggestion = {
                        "rule_name": f"FIRST Beden/Stok Kuralı (Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden)",
                        "original_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={min_stok_per_beden}",
                        "suggested_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden=0",
                            "estimated_new_candidates": additional,
                        "rule_type": "FIRST_size_stock",
                    }
            
            if best_suggestion:
                suggestions.append(best_suggestion)
        
        return suggestions
    
    def _analyze_back_size_stock_rules(self) -> List[Dict]:
        """Analyze BACK size/stock rules and suggest relaxation"""
        suggestions = []
        rules = self.cfg.get("back_size_stock_rules", [])
        if not rules:
            return suggestions
        
        from instagram_auto_post import filter_back_products
        
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        
        # Get current pool
        current_pool = filter_back_products(self.unique_products, cfg_with_calendar)
        
        # Try relaxing each rule
        # Format: rules is a list of tuples: [(size_count, y, z), ...]
        for i, rule in enumerate(rules):
            if len(rule) < 3:
                continue
            size_count, min_beden, min_stok_per_beden = rule[0], rule[1], rule[2]
            
            # Try more aggressive relaxation: reduce min_stok_per_beden down to 0
            best_suggestion = None
            max_additional = 0
            
            for step in [1, 2, 3, 5, 10]:
                new_stok = max(0, min_stok_per_beden - step)
                if new_stok >= min_stok_per_beden:
                    continue
                
                new_rules = rules.copy()
                new_rules[i] = (size_count, min_beden, new_stok)
                
                test_cfg = self.cfg.copy()
                test_cfg["back_size_stock_rules"] = new_rules
                test_cfg["_calendar_for_pool"] = self.calendar
                
                test_pool = filter_back_products(self.unique_products, test_cfg)
                additional = len(test_pool) - len(current_pool)
                
                if additional > max_additional:
                    max_additional = additional
                    best_suggestion = {
                        "rule_name": f"BACK Beden/Stok Kuralı (Size_Count={size_count}, Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden)",
                        "original_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={min_stok_per_beden}",
                        "suggested_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={new_stok}",
                        "estimated_new_candidates": additional,
                        "rule_type": "BACK_size_stock",
                    }
            
            # Also try setting to 0
            if min_stok_per_beden > 0:
                new_rules = rules.copy()
                new_rules[i] = (size_count, min_beden, 0)
                test_cfg = self.cfg.copy()
                test_cfg["back_size_stock_rules"] = new_rules
                test_cfg["_calendar_for_pool"] = self.calendar
                test_pool = filter_back_products(self.unique_products, test_cfg)
                additional = len(test_pool) - len(current_pool)
                if additional > max_additional:
                    max_additional = additional
                    best_suggestion = {
                        "rule_name": f"BACK Beden/Stok Kuralı (Size_Count={size_count}, Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden)",
                        "original_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden={min_stok_per_beden}",
                        "suggested_value": f"Min_Beden_Adedi={min_beden}, Min_Stok_Per_Beden=0",
                            "estimated_new_candidates": additional,
                        "rule_type": "BACK_size_stock",
                    }
            
            if best_suggestion:
                suggestions.append(best_suggestion)
        
        return suggestions
    
    def _analyze_one_atilma_constraint(self) -> List[Dict]:
        """Analyze One Atilma Tarihi constraint and suggest relaxation"""
        suggestions = []
        
        min_days = self.cfg.get("one_atilma_min_days", 0)
        ref_date_str = self.cfg.get("one_atilma_reference_date", "")
        
        if min_days == 0 or not ref_date_str:
            return suggestions
        
        # Get base pool without One Atilma Tarihi filter
        cfg_without_one_atilma = self.cfg.copy()
        cfg_without_one_atilma["one_atilma_min_days"] = 0  # Disable filter
        cfg_without_one_atilma["_calendar_for_pool"] = self.calendar
        
        from instagram_auto_post import filter_first_products
        
        # Pool with One Atilma Tarihi filter
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        pool_with_filter = filter_first_products(self.unique_products, cfg_with_calendar)
        
        # Pool without One Atilma Tarihi filter
        pool_without_filter = filter_first_products(self.unique_products, cfg_without_one_atilma)
        
        blocked_count = len(pool_without_filter) - len(pool_with_filter)
        
        if blocked_count > 0:
            # Try different relaxation values
            for new_days in [max(0, min_days - 15), max(0, min_days - 30), max(0, min_days - 45)]:
                if new_days >= min_days:
                    continue
                
                # Calculate how many products would become available with this relaxation
                test_cfg = self.cfg.copy()
                test_cfg["one_atilma_min_days"] = new_days
                test_cfg["_calendar_for_pool"] = self.calendar
                
                test_pool = filter_first_products(self.unique_products, test_cfg)
                additional_products = len(test_pool) - len(pool_with_filter)
                
                if additional_products > 0:
                    suggestions.append({
                        "rule_name": "One Atilma Tarihi Minimum Gün Sayısı",
                        "original_value": min_days,
                        "suggested_value": new_days,
                        "estimated_new_candidates": additional_products,
                        "rule_type": "one_atilma_days",
                        "note": f"Havuzda {blocked_count} ürün One Atilma Tarihi kısıtı nedeniyle kullanılamıyor"
                    })
                    break
        
        return suggestions
    
    def _analyze_advanced_first_constraints(self, posts: Optional[List[Dict]] = None) -> List[Dict]:
        """Analyze advanced FIRST constraints (black limit, max KisaKod uses) and calculate pool impact"""
        suggestions = []
        
        # Get base pool (with advanced constraints applied)
        cfg_with_calendar = self.cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = self.calendar
        from instagram_auto_post import filter_first_products
        from product_helpers import is_black_color
        
        base_first_candidates = filter_first_products(self.unique_products, cfg_with_calendar)
        
        max_black_per_day = self.cfg.get("max_black_first_per_day", 0)
        if max_black_per_day > 0:
            # Calculate how many black products are in pool
            black_products = base_first_candidates[
                base_first_candidates["Renk"].apply(lambda r: is_black_color(str(r) if pd.notna(r) else ""))
            ]
            black_count_in_pool = len(black_products)
            
            # Calculate max usable black products with current limit
            num_days = len(set(p["day_name"] for p in posts)) if posts else len(set(slot["day_name"] for slot in self.calendar))
            max_usable_black = max_black_per_day * num_days
            
            # Calculate how many black products are blocked by the limit
            blocked_black = max(0, black_count_in_pool - max_usable_black)
            
            if posts:
                posts_by_day = {}
                for p in posts:
                    day = p["day_name"]
                    if day not in posts_by_day:
                        posts_by_day[day] = []
                    posts_by_day[day].append(p)
                
                violations = []
                for day, day_posts in posts_by_day.items():
                    black_count = sum(1 for p in day_posts if is_black_color(p["first_product"].get("Renk", "")))
                    if black_count > max_black_per_day:
                        violations.append((day, black_count))
                
                if violations:
                    max_black_found = max(count for _, count in violations)
                    # Calculate pool impact: if we relax to max_black_found, how many more black products become usable?
                    new_max_usable = max_black_found * num_days
                    additional_usable = max(0, min(blocked_black, new_max_usable - max_usable_black))
                    
                    suggestions.append({
                        "rule_name": "Günlük SİYAH FIRST Limiti",
                        "original_value": max_black_per_day,
                        "suggested_value": max_black_found,
                        "estimated_new_candidates": additional_usable,
                        "rule_type": "black_limit"
                    })
                elif blocked_black > 0:
                    # No violations, but calculate impact if we relax by 1
                    new_max_usable = (max_black_per_day + 1) * num_days
                    additional_usable = max(0, min(blocked_black, new_max_usable - max_usable_black))
                    
                    suggestions.append({
                        "rule_name": "Günlük SİYAH FIRST Limiti",
                        "original_value": max_black_per_day,
                        "suggested_value": max_black_per_day + 1,
                        "estimated_new_candidates": additional_usable,
                        "rule_type": "black_limit",
                        "note": f"Havuzda {blocked_black} siyah ürün limit nedeniyle kullanılamıyor"
                    })
            else:
                # No posts yet - calculate theoretical impact
                if blocked_black > 0:
                    new_max_usable = (max_black_per_day + 1) * num_days
                    additional_usable = max(0, min(blocked_black, new_max_usable - max_usable_black))
                    
                suggestions.append({
                    "rule_name": "Günlük SİYAH FIRST Limiti",
                    "original_value": max_black_per_day,
                    "suggested_value": max_black_per_day + 1,
                        "estimated_new_candidates": additional_usable,
                    "rule_type": "black_limit",
                        "note": f"Havuzda {black_count_in_pool} siyah ürün var, limit ile {max_usable_black} kullanılabilir"
                })
        
        max_kisakod_uses = self.cfg.get("max_first_uses_per_kisakod", 0)
        if max_kisakod_uses > 0:
            kisakod_counts = base_first_candidates["KisaKod"].value_counts()
            kisakods_to_limit = kisakod_counts[kisakod_counts > max_kisakod_uses].index
            
            if not kisakods_to_limit.empty:
                blocked_by_limit = sum(count - max_kisakod_uses for count in kisakod_counts[kisakods_to_limit])
                
                if posts:
                    # Count actual violations in posts
                    from collections import Counter
                    kisakod_usage = Counter()
                    for p in posts:
                        if p.get("first_product"):
                            kisakod = p["first_product"].get("KisaKod", "")
                            if kisakod:
                                kisakod_usage[kisakod] += 1
                    
                    max_uses_found = max(kisakod_usage.values()) if kisakod_usage else 0
                    if max_uses_found > max_kisakod_uses:
                        additional_usable = min(blocked_by_limit, max_uses_found - max_kisakod_uses)
                        
                        suggestions.append({
                            "rule_name": "KisaKod FIRST Kullanım Limiti",
                            "original_value": max_kisakod_uses,
                            "suggested_value": max_uses_found,
                            "estimated_new_candidates": additional_usable,
                            "rule_type": "kisakod_uses"
                        })
                elif blocked_by_limit > 0:
                    # No posts yet - calculate theoretical impact
                    additional_usable = min(blocked_by_limit, 1)  # Estimate: relaxing by 1 allows 1 more per KisaKod
                    
                    suggestions.append({
                        "rule_name": "KisaKod FIRST Kullanım Limiti",
                        "original_value": max_kisakod_uses,
                        "suggested_value": max_kisakod_uses + 1,
                        "estimated_new_candidates": additional_usable,
                        "rule_type": "kisakod_uses",
                        "note": f"Havuzda {blocked_by_limit} ürün limit nedeniyle kullanılamıyor"
                    })
        
        return suggestions
    
    def _analyze_per_day_constraints(self, posts: Optional[List[Dict]] = None) -> List[Dict]:
        """Analyze per-day constraints (min gap days, color/uruncinsi diversity) and calculate pool impact"""
        suggestions = []
        
        min_gap_days = self.cfg.get("same_kisakod_min_gap_days", 0)
        if min_gap_days > 0:
            # Estimate pool impact: reducing gap days allows more products to be used
            # This is a heuristic - actual impact depends on assignment
            if posts:
                # Count violations in actual posts
                from collections import defaultdict
                kisakod_last_day = {}
                violations = []
                
                for day_idx, p in enumerate(posts):
                    if p.get("first_product"):
                        kisakod = p["first_product"].get("KisaKod", "")
                        if kisakod:
                            if kisakod in kisakod_last_day:
                                gap = day_idx - kisakod_last_day[kisakod]
                                if gap < min_gap_days:
                                    violations.append((kisakod, gap))
                            kisakod_last_day[kisakod] = day_idx
                
                if violations:
                    min_gap_found = min(gap for _, gap in violations)
                    suggestions.append({
                        "rule_name": "Ayni KisaKod Minimum Ara Gün",
                        "original_value": min_gap_days,
                        "suggested_value": min_gap_found,
                        "estimated_new_candidates": len(violations),  # Estimate: each violation might allow 1 more product
                        "rule_type": "min_gap_days"
                    })
            else:
                # No posts yet - estimate theoretical impact
                # Estimate: reducing gap by 1 might allow ~10% more products (heuristic)
                from instagram_auto_post import filter_first_products
                cfg_with_calendar = self.cfg.copy()
                cfg_with_calendar["_calendar_for_pool"] = self.calendar
                base_pool = filter_first_products(self.unique_products, cfg_with_calendar)
                
                estimated_impact = max(1, len(base_pool) // 10)  # Heuristic: 10% of pool
                
                suggestions.append({
                    "rule_name": "Ayni KisaKod Minimum Ara Gün",
                    "original_value": min_gap_days,
                    "suggested_value": max(0, min_gap_days - 1),
                    "estimated_new_candidates": estimated_impact,
                    "rule_type": "min_gap_days",
                    "note": "Tahmini etki (atama kısıtı, havuzu doğrudan etkilemez ama atama esnekliğini artırır)"
                })
        
        # Analyze color/uruncinsi diversity constraints
        min_distinct_color = self.cfg.get("min_distinct_color_per_day", 0)
        if min_distinct_color > 0 and posts:
            # Count violations
            from collections import defaultdict
            violations = []
            for p in posts:
                day = p.get("day_name", "")
                if day:
                    day_posts = [pp for pp in posts if pp.get("day_name") == day]
                    distinct_colors = len(set(
                        pp["first_product"].get("Renk", "") 
                        for pp in day_posts 
                        if pp.get("first_product")
                    ))
                    if distinct_colors < min_distinct_color:
                        violations.append((day, distinct_colors))
            
            if violations:
                min_color_found = min(count for _, count in violations)
                suggestions.append({
                    "rule_name": "Günlük Minimum Farklı Renk",
                    "original_value": min_distinct_color,
                    "suggested_value": min_color_found,
                    "estimated_new_candidates": len(violations),  # Estimate
                    "rule_type": "min_distinct_color"
                })
        
        min_distinct_uruncinsi = self.cfg.get("min_distinct_uruncinsi_per_day", 0)
        if min_distinct_uruncinsi > 0 and posts:
            # Count violations
            from collections import defaultdict
            violations = []
            for p in posts:
                day = p.get("day_name", "")
                if day:
                    day_posts = [pp for pp in posts if pp.get("day_name") == day]
                    distinct_uruncinsi = len(set(
                        pp["first_product"].get("UrunCinsi", "") 
                        for pp in day_posts 
                        if pp.get("first_product")
                    ))
                    if distinct_uruncinsi < min_distinct_uruncinsi:
                        violations.append((day, distinct_uruncinsi))
            
            if violations:
                min_uruncinsi_found = min(count for _, count in violations)
                suggestions.append({
                    "rule_name": "Günlük Minimum Farklı Ürün Cinsi",
                    "original_value": min_distinct_uruncinsi,
                    "suggested_value": min_uruncinsi_found,
                    "estimated_new_candidates": len(violations),  # Estimate
                    "rule_type": "min_distinct_uruncinsi"
                })
        
        return suggestions
    
    def _analyze_global_stock_targets_standalone(self) -> List[Dict]:
        """Analyze global stock targets without requiring posts (for initial analysis)"""
        suggestions = []
        
        from instagram_auto_post import filter_first_products, filter_back_products
        
        # Get base pools
        first_candidates = filter_first_products(self.unique_products, self.cfg)
        back_candidates = filter_back_products(self.unique_products, self.cfg)
        
        # Calculate total available stock in pools
        first_pool_stock_sum = first_candidates["total_stock"].sum() if len(first_candidates) > 0 else 0
        back_pool_stock_sum = back_candidates["total_stock"].sum() if len(back_candidates) > 0 else 0
        total_pool_stock_sum = first_pool_stock_sum + back_pool_stock_sum
        
        global_min_first = self.cfg.get("global_min_first_stock_sum", 0)
        try:
            global_min_first = float(global_min_first) if global_min_first else 0
        except (ValueError, TypeError):
            global_min_first = 0
        
        if global_min_first > 0:
            if first_pool_stock_sum < global_min_first:
                suggested_value = max(0, global_min_first * 0.9)
                
                suggestions.append({
                    "rule_name": "Global FIRST Stok Hedefi",
                    "original_value": global_min_first,
                    "suggested_value": suggested_value,
                    "estimated_new_candidates": 0,  # Direct pool size not affected, but selection criteria relaxed
                    "rule_type": "global_first_stock",
                    "note": f"Mevcut FIRST havuz stoku ({first_pool_stock_sum}) hedefin altında. Hedefi düşürmek, daha fazla ürünün plana dahil edilmesine yardımcı olabilir."
                })
            else:
                suggestions.append({
                    "rule_name": "Global FIRST Stok Hedefi",
                    "original_value": global_min_first,
                    "suggested_value": max(0, global_min_first * 0.9),
                    "estimated_new_candidates": 0,
                    "rule_type": "global_first_stock",
                    "note": f"Mevcut FIRST havuz stoku ({first_pool_stock_sum}) yeterli. Ancak hedefi düşürmek, planlama esnekliğini artırabilir."
                })
        
        global_min_total = self.cfg.get("global_min_total_stock_sum", 0)
        try:
            global_min_total = float(global_min_total) if global_min_total else 0
        except (ValueError, TypeError):
            global_min_total = 0
        
        if global_min_total > 0:
            if total_pool_stock_sum < global_min_total:
                suggested_value = max(0, global_min_total * 0.9)
                
                suggestions.append({
                    "rule_name": "Global Toplam Stok Hedefi",
                    "original_value": global_min_total,
                    "suggested_value": suggested_value,
                    "estimated_new_candidates": 0,
                    "rule_type": "global_total_stock",
                    "note": f"Mevcut toplam havuz stoku ({total_pool_stock_sum}) hedefin altında. Hedefi düşürmek, daha fazla ürünün plana dahil edilmesine yardımcı olabilir."
                })
            else:
                suggestions.append({
                    "rule_name": "Global Toplam Stok Hedefi",
                    "original_value": global_min_total,
                    "suggested_value": max(0, global_min_total * 0.9),
                    "estimated_new_candidates": 0,
                    "rule_type": "global_total_stock",
                    "note": f"Mevcut toplam havuz stoku ({total_pool_stock_sum}) yeterli. Ancak hedefi düşürmek, planlama esnekliğini artırabilir."
                })
        
        return suggestions
    
    def _analyze_global_stock_targets(self, posts: List[Dict]) -> List[Dict]:
        """Analyze global stock targets with actual posts (for post-assignment analysis)"""
        suggestions = []
        
        # Calculate actual stock in posts
        first_stock_actual = sum(
            p["first_product"].get("total_stock", 0) 
            for p in posts 
            if p.get("first_product")
        )
        
        back_stock_actual = sum(
            sum(b.get("total_stock", 0) for b in p.get("back_products", []))
            for p in posts
        )
        total_stock_actual = first_stock_actual + back_stock_actual
        
        global_min_first = self.cfg.get("global_min_first_stock_sum", 0)
        try:
            global_min_first = float(global_min_first) if global_min_first else 0
        except (ValueError, TypeError):
            global_min_first = 0
        
        if global_min_first > 0 and first_stock_actual < global_min_first:
            suggested_value = max(0, global_min_first * 0.9)
            
            suggestions.append({
                "rule_name": "Global FIRST Stok Hedefi",
                "original_value": global_min_first,
                "suggested_value": suggested_value,
                "estimated_new_candidates": 0,  # Direct pool size not affected
                "rule_type": "global_first_stock",
                "note": f"Mevcut plan FIRST stoku ({first_stock_actual}) hedefin altında"
            })
        
        global_min_total = self.cfg.get("global_min_total_stock_sum", 0)
        try:
            global_min_total = float(global_min_total) if global_min_total else 0
        except (ValueError, TypeError):
            global_min_total = 0
        
        if global_min_total > 0 and total_stock_actual < global_min_total:
            suggested_value = max(0, global_min_total * 0.9)
            
            suggestions.append({
                "rule_name": "Global Toplam Stok Hedefi",
                "original_value": global_min_total,
                "suggested_value": suggested_value,
                "estimated_new_candidates": 0,
                "rule_type": "global_total_stock",
                "note": f"Mevcut plan toplam stoku ({total_stock_actual}) hedefin altında"
            })
        
        return suggestions
    
    def apply_relaxations(self, suggestions: List[Dict]) -> Dict:
        """
        Apply selected relaxation suggestions to configuration.
        
        Args:
            suggestions: List of relaxation suggestion dictionaries
            
        Returns:
            New configuration dictionary with relaxations applied
        """
        new_cfg = self.cfg.copy()
        
        for sug in suggestions:
            rule_type = sug.get("rule_type")
            suggested_value = sug.get("suggested_value")
            
            if rule_type == "FIRST_stock":
                new_cfg["min_total_stock_front"] = suggested_value
            elif rule_type == "BACK_stock":
                new_cfg["min_total_stock_back"] = suggested_value
            elif rule_type == "FIRST_size_stock":
                # Parse suggested_value to extract new rule
                # Format: "Min_Beden_Adedi=X, Min_Stok_Per_Beden=Y"
                # For now, try to find and update the matching rule
                rules = new_cfg.get("front_size_stock_rules", [])
                if rules and suggested_value:
                    # Try to extract values from suggested_value string
                    # This is a simplified approach - may need refinement
                    pass  # Keep existing rules for now
            elif rule_type == "BACK_size_stock":
                # Similar to FIRST_size_stock
                pass  # Keep existing rules for now
            elif rule_type == "one_atilma_days":
                new_cfg["one_atilma_min_days"] = suggested_value
            elif rule_type == "black_limit":
                new_cfg["max_black_first_per_day"] = suggested_value
            elif rule_type == "kisakod_uses":
                new_cfg["max_first_uses_per_kisakod"] = suggested_value
            elif rule_type == "min_gap_days":
                new_cfg["same_kisakod_min_gap_days"] = suggested_value
            elif rule_type == "min_distinct_color":
                new_cfg["min_distinct_color_per_day"] = suggested_value
            elif rule_type == "min_distinct_uruncinsi":
                new_cfg["min_distinct_uruncinsi_per_day"] = suggested_value
            elif rule_type == "global_first_stock":
                new_cfg["global_min_first_stock_sum"] = suggested_value
            elif rule_type == "global_total_stock":
                new_cfg["global_min_total_stock_sum"] = suggested_value
        
        return new_cfg
