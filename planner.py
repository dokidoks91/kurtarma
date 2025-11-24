#!/usr/bin/env python3
"""
Instagram Post Planner - Core Business Logic Module

This module contains the refactored planning logic from instagram_auto_post.py.
It can be called from CLI, GUI, or any other interface.

Supports interactive best-effort mode with two-pass flow:
1. Strict pass: Try to generate plan with original config
2. If fails: Show dialog with relaxation suggestions
3. Best-effort pass: Apply relaxations and re-run (if user chooses)
"""

import os
from copy import deepcopy
from typing import Optional, Tuple, List, Dict, Any
import pandas as pd
from best_effort_analyzer import BestEffortAnalyzer
from instagram_auto_post import (
    DEFAULT_CFG,
    load_stock_data,
    build_unique_products,
    build_post_calendar,
    filter_first_products,
    filter_back_products,
    run_constraint_analyzer,
    assign_first_products,
    check_advanced_first_constraints,
    check_weekly_nos_dvm,
    assign_back_products,
    export_to_excel,
    export_to_markdown,
    print_summary,
)


def _summarize_missing_counts(
    calendar: List[Dict[str, Any]],
    first_pool_size: int,
    back_pool_size: int,
    placed_first: int,
    placed_back: int,
    fallback_reason: str = "",
) -> Dict[str, Any]:
    """
    Calculate required, available, and missing counts for FIRST and BACK products.
    
    Returns comprehensive pool and shortage information for display in GUI.
    """
    required_first = len(calendar)
    required_back = len(calendar) * 9
    
    # Pool-based shortages (based on available products in pool)
    pool_missing_first = max(0, required_first - first_pool_size)
    pool_missing_back = max(0, required_back - back_pool_size)
    
    # Assignment-based shortages (based on actual placement in trial)
    assign_missing_first = max(0, required_first - placed_first)
    assign_missing_back = max(0, required_back - placed_back)
    
    # Use assignment data if available (more accurate), otherwise use pool data
    use_assignment = placed_first > 0 or placed_back > 0
    missing_first = assign_missing_first if use_assignment else pool_missing_first
    missing_back = assign_missing_back if use_assignment else pool_missing_back
    
    return {
        # Required counts for this plan
        "required_first": required_first,
        "required_back": required_back,
        
        # Available products in pool (based on current criteria)
        "available_first": first_pool_size,
        "available_back": back_pool_size,
        
        # Missing counts (final calculation)
        "missing_first": missing_first,
        "missing_back": missing_back,
        
        # Detailed breakdown for diagnostics
        "pool_missing_first": pool_missing_first,
        "pool_missing_back": pool_missing_back,
        "assign_missing_first": assign_missing_first,
        "assign_missing_back": assign_missing_back,
        "placed_first": placed_first,
        "placed_back": placed_back,
        "fallback_reason": fallback_reason,
    }


def _dedupe_relaxations(relaxations: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not relaxations:
        return []
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for sug in relaxations:
        if not isinstance(sug, dict):
            continue
        key = (
            sug.get("rule_type"),
            sug.get("rule_name"),
            sug.get("suggested_value"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sug)
    return deduped


def run_planner_with_best_effort(
    excel_path: str,
    start_day: str,
    num_days: int,
    mode_front: str = "Her ikisi",
    mode_back: str = "Her ikisi",
    on_progress=None,
    on_relaxation_choice=None,
    config_override=None,
) -> dict:
    """
    Two-pass planner with interactive best-effort mode.
    
    PASS 1 (Strict): Try to generate plan with original config
    PASS 2 (Best-effort): If fails, show dialog and optionally apply relaxations
    
    Args:
        excel_path: Path to stock Excel file
        start_day: Starting day name in Turkish
        num_days: Number of days to plan (1-7)
        mode_front: Front product seasonal mode
        mode_back: Back product seasonal mode
        on_progress: Callback for progress updates
        on_relaxation_choice: Callback(suggestions, message) -> choice
            Returns: "manual" (user will adjust), "apply" (apply relaxations), "abort" (cancel)
        config_override: Optional config dict
        
    Returns:
        dict with success, summary_text, output files, and relaxations_applied
    """
    
    def emit(msg: str):
        """Helper to print and call on_progress callback"""
        print(msg)
        if on_progress:
            on_progress(msg)
    
    try:
        emit("=" * 70)
        emit("PASS 1: Strict mode - trying with original config")
        emit("=" * 70)
        
        if config_override:
            min_gap_value = config_override.get("same_kisakod_min_gap_days", "NOT_SET")
            emit(f"🔍 DEBUG: same_kisakod_min_gap_days at strict pass start = {min_gap_value}")
        
        result = run_planner(
            excel_path=excel_path,
            start_day=start_day,
            num_days=num_days,
            mode_front=mode_front,
            mode_back=mode_back,
            on_progress=on_progress,
            on_decision=None,  # No interactive decisions in strict pass
            config_override=config_override,
        )
        
        if result["success"]:
            emit("\n✓ Strict mode succeeded - plan generated without relaxations")
            result["relaxations_applied"] = []
            result["preferred_first_report"] = []
            return result
        
        emit("\n⚠️  Strict mode failed - analyzing constraints...")
        
        if config_override:
            cfg = config_override.copy()
        else:
            cfg = DEFAULT_CFG.copy()
            cfg["stock_excel_path"] = excel_path
            cfg["plan_start_day_name"] = start_day
            cfg["plan_num_days"] = num_days
        
        # Store original config for retry without relaxations
        original_cfg = cfg.copy()
        
        raw_df = load_stock_data(cfg)
        unique_products = build_unique_products(raw_df)
        calendar = build_post_calendar(cfg)
        missing_stats = _summarize_missing_counts(calendar, 0, 0, 0, 0)
        preferred_report: List[Dict[str, Any]] = []
        applied_relaxations: List[Dict[str, Any]] = []
        current_cfg = cfg.copy()
        
        emit(f"\n🔍 Prioritization config:")
        emit(f"   prioritize_by_newness = {cfg.get('prioritize_by_newness', False)}")
        emit(f"   prioritize_by_stock = {cfg.get('prioritize_by_stock', False)}")
        
        preferred_products = cfg.get("preferred_first_products", [])
        emit(f"\n📋 Preferred FIRST products loaded: {len(preferred_products)} items")
        if preferred_products:
            for i, pref in enumerate(preferred_products[:5], 1):
                kisakodrenk = pref.get("kisakodrenk", "")
                gun = pref.get("gun", "")
                time = pref.get("time", "")
                emit(f"   {i}. {kisakodrenk} - {gun} {time if time else '(herhangi bir saat)'}")
            if len(preferred_products) > 5:
                emit(f"   ... ve {len(preferred_products) - 5} daha")
        
        # Analyze and compute relaxation suggestions (Two-phase approach)
        analyzer = BestEffortAnalyzer(calendar, unique_products, cfg, raw_df)
        
        emit("\n📊 Phase 1: Analyzing pool-based constraints...")
        phase1_result = analyzer.analyze_and_suggest_relaxations(posts=None)
        
        emit("\n📊 Phase 2: Running trial assignment to analyze assignment-based constraints...")
        phase2_suggestions = []
        prioritization_is_blocking = False
        trial_posts: List[Dict[str, Any]] = []
        first_candidates = None
        back_candidates = None
        first_pool_size = 0
        back_pool_size = 0
        try:
            # Pass calendar info to cfg for advanced constraint filtering in pool calculation
            cfg_with_calendar = cfg.copy()
            cfg_with_calendar["_calendar_for_pool"] = calendar
            first_candidates = filter_first_products(unique_products, cfg_with_calendar)
            first_pool_size = len(first_candidates)
            trial_posts = assign_first_products(calendar, first_candidates, cfg, decide=lambda msg: True)
            preferred_report = cfg.pop("_preferred_assignment_report", [])
            
            if trial_posts:
                back_candidates = filter_back_products(unique_products, cfg_with_calendar)
                back_pool_size = len(back_candidates)
                trial_posts = assign_back_products(trial_posts, back_candidates, cfg)
                
                phase2_result = analyzer.analyze_and_suggest_relaxations(posts=trial_posts)
                phase2_suggestions = phase2_result["suggestions"]
                emit(f"   Trial assignment produced {len(trial_posts)} posts for analysis")
                
                required_first = len(calendar)
                placed_first = sum(1 for p in trial_posts if p.get("first_product"))
                
                required_back = len(calendar) * 9
                placed_back = sum(len(p.get("back_products", [])) for p in trial_posts)
                
                missing_stats = _summarize_missing_counts(
                    calendar,
                    first_pool_size,
                    back_pool_size,
                    placed_first,
                    placed_back,
                )
                
                emit(f"   Trial counts: {placed_first}/{required_first} FIRST, {placed_back}/{required_back} BACK")
                
                from instagram_auto_post import check_advanced_first_constraints
                constraints_pass = True
                try:
                    constraints_pass = check_advanced_first_constraints(trial_posts, cfg, decide=lambda msg: True)
                except Exception as e:
                    emit(f"   ⚠️  Advanced constraint check failed: {e}")
                    constraints_pass = False
                
                if (
                    missing_stats["missing_first"] == 0
                    and missing_stats["missing_back"] == 0
                    and not constraints_pass
                    and cfg.get("prioritize_by_newness")
                    and not cfg.get("prioritize_by_stock")
                ):
                    emit(f"\n🔍 Detecting prioritization blocking: missing_first=0, missing_back=0, but advanced constraints failed")
                    emit(f"   Current: prioritize_by_newness=True, prioritize_by_stock=False (recency only)")
                    emit(f"   Suggestion: Enable stock as secondary priority to reduce constraint conflicts")
                    prioritization_is_blocking = True
                
                if not constraints_pass:
                    emit(f"   ⚠️  Trial posts violate advanced constraints (max black per day, max KisaKod uses)")
                    emit(f"   Note: Counts show 0/0 but advanced constraints block placement")
                    emit(f"   Actual counts: missing_first={missing_stats['missing_first']}, missing_back={missing_stats['missing_back']}")
            else:
                emit(f"   Trial assignment returned empty - using realistic fallback counts")
                missing_stats = _summarize_missing_counts(
                    calendar,
                    first_pool_size,
                    back_pool_size,
                    0,
                    0,
                    fallback_reason="trial_assignment_empty",
                )
        except Exception as e:
            emit(f"   Trial assignment failed: {e}")
            emit(f"   Using fallback counts (may be inaccurate)")
            missing_stats = _summarize_missing_counts(
                calendar,
                first_pool_size,
                back_pool_size,
                0,
                0,
                fallback_reason=str(e),
            )
        
        if preferred_products and trial_posts and first_candidates is not None:
            emit(f"\n📋 Preferred FIRST products placement check:")
            all_stock_kisakodrenk = set(unique_products["kisakodrenk"].str.upper())
            first_pool_kisakodrenk = set(first_candidates["kisakodrenk"].str.upper())
            placed_kisakodrenk = set(p["first_product"]["kisakodrenk"].upper() for p in trial_posts if p.get("first_product"))
            
            for i, pref in enumerate(preferred_products, 1):
                kisakodrenk = pref.get("kisakodrenk", "").strip().upper()
                if not kisakodrenk:
                    continue
                
                if kisakodrenk not in all_stock_kisakodrenk:
                    emit(f"   ❌ {i}. {kisakodrenk}: Stok dosyasında bulunamadı")
                elif kisakodrenk not in first_pool_kisakodrenk:
                    emit(f"   ⚠️  {i}. {kisakodrenk}: FIRST havuzuna giremedi (sezon/çekim/stok filtreleri)")
                elif kisakodrenk in placed_kisakodrenk:
                    emit(f"   ✓ {i}. {kisakodrenk}: Plana atandı")
                else:
                    emit(f"   ⚠️  {i}. {kisakodrenk}: Havuzda ama atama aşamasında yer bulamadı (günlük kısıtlar)")
        
        all_suggestions = phase1_result["suggestions"] + phase2_suggestions
        seen_rules = {}
        for sug in all_suggestions:
            rule_type = sug["rule_type"]
            rule_name = sug.get("rule_name", rule_type)
            key = (rule_type, rule_name)
            if key not in seen_rules:
                seen_rules[key] = sug
            else:
                existing = seen_rules[key]
                if sug.get("estimated_new_candidates", 0) > existing.get("estimated_new_candidates", 0):
                    seen_rules[key] = sug
        
        suggestions = list(seen_rules.values())
        
        if prioritization_is_blocking:
            priority_suggestion = {
                "rule_type": "PRIORITY_mode",
                "original_value": "Yalnızca yeniliğe göre",
                "suggested_value": "Yenilik + stok (ikincil öncelik)",
                "estimated_new_candidates": 9999,
                "note": "Atama kısıtlarıyla çakışmaları azaltır (yüksek etki)",
                "preselected": True
            }
            suggestions.append(priority_suggestion)
            emit(f"\n⚠️  Added PRIORITY_mode suggestion: Enable stock as secondary priority")
        
        # Filter out FIRST-only relaxations when missing_first == 0
        filtered_suggestions = []
        for sug in suggestions:
            if (
                sug["rule_type"] in ["FIRST_stock", "FIRST_size_stock"]
                and missing_stats["missing_first"] == 0
            ):
                # Skip FIRST-only relaxations when FIRST slots are already filled
                continue
            filtered_suggestions.append(sug)
        
        suggestions = filtered_suggestions
        suggestions.sort(key=lambda s: s.get("estimated_new_candidates", 0), reverse=True)
        
        # Calculate total estimated impact (only for pool-based relaxations)
        pool_based_impact = sum(
            s.get("estimated_new_candidates", 0)
            for s in suggestions
            if s.get("rule_type") in ["BACK_stock", "BACK_size_stock", "FIRST_stock", "FIRST_size_stock"]
        )
        
        # Add informative note about impact vs missing count
        if missing_stats["missing_back"] > 0:
            if pool_based_impact < missing_stats["missing_back"]:
                impact_note = {
                    "rule_name": "ℹ️ Tahmini Etki vs Eksik Sayı",
                    "original_value": f"Toplam havuz etkisi: ~{pool_based_impact} yeni aday",
                    "suggested_value": f"Eksik BACK: {missing_stats['missing_back']} ürün",
                    "estimated_new_candidates": 0,
                    "rule_type": "impact_summary",
                    "note": f"Havuz tabanlı esnetmeler ~{pool_based_impact} yeni BACK adayı sağlayabilir. Eksik sayı {missing_stats['missing_back']} olduğu için, günlük kısıt esnetmeleri veya birden fazla esnetme kombinasyonu gerekebilir. 'Best-effort' modu tüm esnetmeleri uygulayarak en iyi sonucu üretmeye çalışacaktır.",
                    "preselected": False
                }
                suggestions.insert(0, impact_note)
            else:
                impact_note = {
                    "rule_name": "ℹ️ Tahmini Etki",
                    "original_value": f"Toplam havuz etkisi: ~{pool_based_impact} yeni aday",
                    "suggested_value": f"Eksik BACK: {missing_stats['missing_back']} ürün",
                    "estimated_new_candidates": 0,
                    "rule_type": "impact_summary",
                    "note": f"Havuz tabanlı esnetmeler teorik olarak yeterli aday sağlayabilir. Ancak günlük kısıtlar nedeniyle gerçek atama daha az olabilir.",
                    "preselected": False
                }
                suggestions.insert(0, impact_note)
        
        result = phase1_result
        result["suggestions"] = suggestions
        soft_violations = result["soft_violations"]
        hard_violations = result["hard_violations"]
        diagnostics = result["diagnostics"]
        dialog_message = result["message"]
        
        emit("\n📋 Constraint Diagnostics:")
        emit(f"   FIRST pool: {diagnostics.get('first_pool_size', 0)} candidates (need {diagnostics.get('required_first', 0)})")
        emit(f"   BACK pool: {diagnostics.get('back_pool_size', 0)} candidates (need {diagnostics.get('required_back', 0)})")
        emit(f"   Soft violations: {len(soft_violations)}")
        emit(f"   Hard violations: {len(hard_violations)}")
        emit(f"   Relaxation suggestions: {len(suggestions)}")
        
        if not suggestions and hard_violations:
            hard_rules_list = "\n".join([f"  - {v['rule_name']}: {v['reason']}" for v in hard_violations])
            error_msg = f"Plan oluşturulamadı - sadece esnetilemez (hard) kurallar ihlal edildi:\n\n{hard_rules_list}\n\nBu kurallar esnetilemiyor. Lütfen ayarları manuel olarak düzeltin."
            emit(f"\n❌ {error_msg}")
            return {
                "success": False,
                "summary_text": error_msg,
                "error": "Only hard rules violated",
                "relaxations_applied": [],
                "preferred_first_report": preferred_report,
            }
        
        if not suggestions and soft_violations:
            soft_rules_list = "\n".join([f"  - {v['rule_name']}: {v['reason']}" for v in soft_violations])
            error_msg = f"Plan oluşturulamadı - esnetilebilir kurallar ihlal edildi ancak öneri üretilemedi:\n\n{soft_rules_list}\n\nLütfen ayarları manuel olarak düzeltin."
            emit(f"\n⚠️ {error_msg}")
            return {
                "success": False,
                "summary_text": error_msg,
                "error": "Soft rules violated but no suggestions",
                "relaxations_applied": [],
                "preferred_first_report": preferred_report,
            }
        
        # Even if no suggestions, still show dialog if there are violations
        # This allows user to proceed with best-effort mode
        if not suggestions:
            emit("\n⚠️  Plan oluşturulamadı ancak esnetme önerisi bulunamadı")
            emit("   Kullanıcıya best-effort seçeneği sunulacak")
            # Don't return error - let dialog show with empty suggestions
            # User can still choose to proceed with best-effort
            # But ensure we have at least empty lists for dialog
            if not soft_violations and not hard_violations:
                # No violations detected - this shouldn't happen, but handle gracefully
                emit("   ⚠️  Uyarı: İhlal tespit edilemedi ama plan oluşturulamadı")
        
        emit(f"\n{dialog_message}")
        
        emit(f"\n🔍 Dialog path: INITIAL (first attempt)")
        emit(f"   Suggestions count: {len(suggestions)}")
        emit(
            f"   Actual counts: missing_first={missing_stats['missing_first']}, "
            f"missing_back={missing_stats['missing_back']}"
        )
        
        # Debug: Print detailed suggestion info
        if suggestions:
            emit(f"   Suggestions details:")
            for i, sug in enumerate(suggestions[:5]):  # Show first 5
                emit(f"     {i+1}. {sug.get('rule_name', 'N/A')}: {sug.get('rule_type', 'N/A')}, impact={sug.get('estimated_new_candidates', 0)}")
        else:
            emit(f"   ⚠️  WARNING: No suggestions generated!")
            emit(f"   Phase1 suggestions: {len(phase1_result.get('suggestions', []))}")
            emit(f"   Phase2 suggestions: {len(phase2_suggestions)}")
        
        # ALWAYS show dialog - never auto-apply relaxations without user confirmation
        # Even if missing counts are 0/0, user should see what relaxations are being suggested
        # Even if suggestions is empty, show dialog so user can proceed with best-effort
        if on_relaxation_choice:
            # Pass comprehensive pool/shortage information to GUI
            pool_info = {
                "required_first": missing_stats["required_first"],
                "required_back": missing_stats["required_back"],
                "available_first": missing_stats.get("available_first", 0),
                "available_back": missing_stats.get("available_back", 0),
                "missing_first": missing_stats["missing_first"],
                "missing_back": missing_stats["missing_back"],
            }
            
            # Pass violations to GUI for display
            # Also pass unique_products, calendar, and current_cfg for real-time pool recalculation
            choice, selected_suggestions = on_relaxation_choice(
                suggestions,
                dialog_message,
                missing_stats["missing_first"],
                missing_stats["missing_back"],
                preferred_report,
                soft_violations=soft_violations,
                hard_violations=hard_violations,
                pool_info=pool_info,
                unique_products=unique_products,
                calendar=calendar,
                current_cfg=current_cfg,
            )
            
            if choice == "manual" or choice == "abort":
                emit("\n⏸️  Kullanıcı ayarları manuel düzeltmeyi seçti - plan iptal edildi")
                return {
                    "success": False,
                    "summary_text": "Plan iptal edildi - lütfen ayarları düzeltin ve tekrar deneyin.",
                    "error": "User chose to adjust settings manually",
                    "relaxations_applied": [],
                    "preferred_first_report": preferred_report,
                }
        else:
            # No callback provided - cannot proceed without user input
            emit("\n❌ Relaxation choice callback not provided - cannot proceed")
            return {
                "success": False,
                "summary_text": "Plan oluşturulamadı - relaxation seçimi gerekli ancak callback sağlanmadı.",
                "error": "No relaxation choice callback",
                "relaxations_applied": [],
                "preferred_first_report": preferred_report,
            }
        
        if choice == "retry_strict":
            emit("\n" + "=" * 70)
            emit("Retry: Applying selected relaxations and retrying strict mode")
            emit("=" * 70)
            
            max_retries = 3
            retry_count = 0
            previous_suggestions_signature = None
            exited_via_continue_best = False
            
            while retry_count < max_retries:
                retry_count += 1
                emit(f"\n🔄 Retry attempt {retry_count}/{max_retries}")
                
                analyzer_for_apply = BestEffortAnalyzer(calendar, unique_products, current_cfg, raw_df)
                relaxed_cfg = analyzer_for_apply.apply_relaxations(selected_suggestions)
                
                if relaxed_cfg == current_cfg:
                    emit("\n⚠️  Selected relaxations produced no config changes - stopping retry loop")
                    return {
                        "success": False,
                        "summary_text": "Seçili esnetmeler yapılandırmayı değiştirmedi. Lütfen farklı kurallar seçin veya ayarları manuel düzeltin.",
                        "error": "No config changes from selected relaxations",
                        "relaxations_applied": selected_suggestions,
                        "preferred_first_report": preferred_report,
                    }
                
                current_cfg = relaxed_cfg.copy()
                applied_relaxations.extend(selected_suggestions)
                
                result = run_planner(
                    excel_path=excel_path,
                    start_day=start_day,
                    num_days=num_days,
                    mode_front=mode_front,
                    mode_back=mode_back,
                    on_progress=on_progress,
                    on_decision=None,
                    config_override=current_cfg,
                )
                
                if result["success"]:
                    emit(f"\n✓ Retry succeeded after {retry_count} attempt(s)")
                    result["relaxations_applied"] = _dedupe_relaxations(applied_relaxations)
                    result["preferred_first_report"] = preferred_report
                    return result
                
                emit(f"\n⚠️  Retry attempt {retry_count} failed - analyzing again...")
                
                analyzer_retry = BestEffortAnalyzer(calendar, unique_products, current_cfg, raw_df)
                phase1_retry = analyzer_retry.analyze_and_suggest_relaxations(posts=None)
                
                try:
                    current_cfg_with_calendar = current_cfg.copy()
                    current_cfg_with_calendar["_calendar_for_pool"] = calendar
                    first_candidates_retry = filter_first_products(unique_products, current_cfg_with_calendar)
                    first_pool_size_retry = len(first_candidates_retry)
                    trial_posts_retry = assign_first_products(calendar, first_candidates_retry, current_cfg, decide=lambda msg: True)
                    
                    back_pool_size_retry = 0
                    if trial_posts_retry:
                        back_candidates_retry = filter_back_products(unique_products, current_cfg_with_calendar)
                        back_pool_size_retry = len(back_candidates_retry)
                        trial_posts_retry = assign_back_products(trial_posts_retry, back_candidates_retry, current_cfg)
                        
                        phase2_retry = analyzer_retry.analyze_and_suggest_relaxations(posts=trial_posts_retry)
                        phase2_suggestions_retry = phase2_retry["suggestions"]
                        
                        required_first_retry = len(calendar)
                        placed_first_retry = sum(1 for p in trial_posts_retry if p.get("first_product"))
                        
                        required_back_retry = len(calendar) * 9
                        placed_back_retry = sum(len(p.get("back_products", [])) for p in trial_posts_retry)
                        
                        missing_stats = _summarize_missing_counts(
                            calendar,
                            first_pool_size_retry,
                            back_pool_size_retry,
                            placed_first_retry,
                            placed_back_retry,
                        )
                    else:
                        emit(f"   Trial assignment returned empty - using realistic fallback counts")
                        phase2_suggestions_retry = []
                        missing_stats = _summarize_missing_counts(
                            calendar,
                            first_pool_size_retry,
                            back_pool_size_retry,
                            0,
                            0,
                            fallback_reason="retry_trial_empty",
                        )
                except Exception as e:
                    emit(f"   Trial assignment failed: {e}")
                    emit(f"   Using fallback counts (may be inaccurate)")
                    phase2_suggestions_retry = []
                    missing_stats = _summarize_missing_counts(
                        calendar,
                        0,
                        0,
                        0,
                        0,
                        fallback_reason=str(e),
                    )
                
                all_suggestions_retry = phase1_retry["suggestions"] + phase2_suggestions_retry
                seen_rules_retry = {}
                for sug in all_suggestions_retry:
                    rule_type = sug["rule_type"]
                    rule_name = sug.get("rule_name", rule_type)
                    key = (rule_type, rule_name)
                    if key not in seen_rules_retry:
                        seen_rules_retry[key] = sug
                    else:
                        existing = seen_rules_retry[key]
                        if sug.get("estimated_new_candidates", 0) > existing.get("estimated_new_candidates", 0):
                            seen_rules_retry[key] = sug
                
                suggestions_retry = list(seen_rules_retry.values())
                
                # Filter out FIRST-only relaxations when missing_first == 0 (same as initial)
                filtered_suggestions_retry = []
                for sug in suggestions_retry:
                    if (
                        sug["rule_type"] in ["FIRST_stock", "FIRST_size_stock"]
                        and missing_stats["missing_first"] == 0
                    ):
                        continue
                    filtered_suggestions_retry.append(sug)
                
                suggestions_retry = filtered_suggestions_retry
                suggestions_retry.sort(key=lambda s: s.get("estimated_new_candidates", 0), reverse=True)
                
                # Add impact summary for retry as well
                pool_based_impact_retry = sum(
                    s.get("estimated_new_candidates", 0)
                    for s in suggestions_retry
                    if s.get("rule_type") in ["BACK_stock", "BACK_size_stock", "FIRST_stock", "FIRST_size_stock"]
                )
                
                if missing_stats["missing_back"] > 0 and pool_based_impact_retry < missing_stats["missing_back"]:
                    impact_note_retry = {
                        "rule_name": "ℹ️ Tahmini Etki vs Eksik Sayı",
                        "original_value": f"Toplam havuz etkisi: ~{pool_based_impact_retry} yeni aday",
                        "suggested_value": f"Eksik BACK: {missing_stats['missing_back']} ürün",
                        "estimated_new_candidates": 0,
                        "rule_type": "impact_summary",
                        "note": f"Havuz tabanlı esnetmeler ~{pool_based_impact_retry} yeni BACK adayı sağlayabilir. Eksik sayı {missing_stats['missing_back']} olduğu için, günlük kısıt esnetmeleri veya birden fazla esnetme kombinasyonu gerekebilir.",
                        "preselected": False
                    }
                    suggestions_retry.insert(0, impact_note_retry)
                
                if not suggestions_retry:
                    emit("\n❌ No more relaxation suggestions available")
                    return {
                        "success": False,
                        "summary_text": "Esnetmeler uygulandı ancak plan hala oluşturulamadı ve daha fazla öneri yok.",
                        "error": "No more suggestions after retry",
                        "relaxations_applied": selected_suggestions,
                        "preferred_first_report": preferred_report,
                    }
                
                current_suggestions_signature = tuple(sorted([
                    (s["rule_type"], s.get("rule_name", s["rule_type"]), s.get("suggested_value", ""))
                    for s in suggestions_retry
                ]))
                
                if previous_suggestions_signature is not None and current_suggestions_signature == previous_suggestions_signature:
                    emit("\n⚠️  Suggestions unchanged from previous iteration - stopping retry loop")
                    emit(f"   Suggestions signature: {len(current_suggestions_signature)} rules")
                    return {
                        "success": False,
                        "summary_text": "Öneriler değişmedi. Daha fazla esnetme mümkün değil. Lütfen ayarları manuel düzeltin.",
                        "error": "Suggestions unchanged - no convergence",
                        "relaxations_applied": selected_suggestions,
                        "preferred_first_report": preferred_report,
                    }
                
                total_estimated = sum(s.get("estimated_new_candidates", 0) for s in suggestions_retry)
                emit(f"   Total estimated impact: {total_estimated} new candidates")
                
                if total_estimated == 0:
                    emit("\n⚠️  All suggestions have zero estimated impact - stopping retry loop")
                    return {
                        "success": False,
                        "summary_text": "Tüm önerilerin tahmini etkisi sıfır. Daha fazla esnetme fayda sağlamayacak. Lütfen ayarları manuel düzeltin.",
                        "error": "Zero estimated impact - no benefit from relaxations",
                        "relaxations_applied": selected_suggestions,
                        "preferred_first_report": preferred_report,
                    }
                
                previous_suggestions_signature = current_suggestions_signature
                
                emit(f"\n🔍 Dialog path: RETRY (attempt {retry_count})")
                emit(f"   Suggestions count: {len(suggestions_retry)}")
                emit(
                    f"   Actual counts: missing_first={missing_stats['missing_first']}, "
                    f"missing_back={missing_stats['missing_back']}"
                )
                
                if on_relaxation_choice:
                    # Get violations from retry analysis
                    soft_violations_retry = phase1_retry.get("soft_violations", [])
                    hard_violations_retry = phase1_retry.get("hard_violations", [])
                    
                    # Pass comprehensive pool/shortage information to GUI
                    pool_info_retry = {
                        "required_first": missing_stats["required_first"],
                        "required_back": missing_stats["required_back"],
                        "available_first": missing_stats.get("available_first", 0),
                        "available_back": missing_stats.get("available_back", 0),
                        "missing_first": missing_stats["missing_first"],
                        "missing_back": missing_stats["missing_back"],
                    }
                    
                    choice, selected_suggestions = on_relaxation_choice(
                        suggestions_retry,
                        "",
                        missing_stats["missing_first"],
                        missing_stats["missing_back"],
                        preferred_report,
                        soft_violations=soft_violations_retry,
                        hard_violations=hard_violations_retry,
                        pool_info=pool_info_retry,
                        unique_products=unique_products,
                        calendar=calendar,
                        current_cfg=current_cfg,
                    )
                    
                    if choice == "manual" or choice == "abort":
                        emit("\n⏸️  Kullanıcı ayarları manuel düzeltmeyi seçti")
                        return {
                            "success": False,
                            "summary_text": "Plan iptal edildi - lütfen ayarları düzeltin ve tekrar deneyin.",
                            "error": "User chose to adjust settings manually",
                            "relaxations_applied": selected_suggestions,
                            "preferred_first_report": preferred_report,
                        }
                    
                    if choice == "continue_best":
                        exited_via_continue_best = True
                        break
                else:
                    break
            
            if retry_count >= max_retries and not exited_via_continue_best:
                emit(f"\n❌ Maximum retries ({max_retries}) reached without success")
                return {
                    "success": False,
                    "summary_text": f"Maksimum deneme sayısına ({max_retries}) ulaşıldı. Plan oluşturulamadı.",
                    "error": "Max retries reached",
                    "relaxations_applied": _dedupe_relaxations(applied_relaxations or selected_suggestions),
                    "preferred_first_report": preferred_report,
                }
        
        # If user chose to continue without relaxations (selected_suggestions is empty) and missing counts are 0/0,
        # try strict mode one more time with original config
        # IMPORTANT: If strict mode fails, we should NOT proceed with violations - user explicitly chose "no relaxations"
        if not selected_suggestions and missing_stats["missing_first"] == 0 and missing_stats["missing_back"] == 0:
            emit("\n" + "=" * 70)
            emit("PASS 2: Retrying strict mode with original constraints (no relaxations)")
            emit("=" * 70)
            emit("⚠️  Not: Eğer strict mode tekrar başarısız olursa, plan oluşturulamayacak.")
            emit("   Kullanıcı 'esnetme yapma' seçtiği için kısıt ihlalleriyle plan oluşturulmayacak.")
            
            # Retry strict mode with original config - use on_decision=None to enforce strict constraints
            result = run_planner(
                excel_path=excel_path,
                start_day=start_day,
                num_days=num_days,
                mode_front=mode_front,
                mode_back=mode_back,
                on_progress=on_progress,
                on_decision=None,  # Strict mode - enforce all constraints, no violations allowed
                config_override=original_cfg,  # Use original config, not relaxed
            )
            
            if result["success"]:
                emit("\n✓ Strict mode retry succeeded - plan generated with original constraints")
                result["relaxations_applied"] = []
                result["preferred_first_report"] = preferred_report
                return result
            else:
                # Strict mode failed - user chose "no relaxations", so we cannot proceed with violations
                emit("\n❌ Strict mode retry failed - plan oluşturulamadı")
                emit("   Kullanıcı 'esnetme yapma' seçtiği için kısıt ihlalleriyle plan oluşturulamıyor.")
                emit("   Lütfen ayarları manuel olarak düzeltin veya esnetme seçeneklerini kullanın.")
                return {
                    "success": False,
                    "summary_text": "Plan oluşturulamadı - strict mode başarısız oldu ve kullanıcı esnetme yapmayı seçmedi. Lütfen ayarları düzeltin veya esnetme seçeneklerini kullanın.",
                    "error": "Strict mode failed, no relaxations allowed",
                    "relaxations_applied": [],
                    "preferred_first_report": preferred_report,
                }
        
        emit("\n" + "=" * 70)
        emit("PASS 2: Best-effort mode - applying selected relaxations")
        emit("=" * 70)
        
        final_apply_analyzer = BestEffortAnalyzer(calendar, unique_products, current_cfg, raw_df)
        relaxed_cfg = final_apply_analyzer.apply_relaxations(selected_suggestions)
        current_cfg = relaxed_cfg.copy()
        applied_relaxations.extend(selected_suggestions)
        
        # Determine on_decision behavior based on whether relaxations were selected
        # If no relaxations selected, enforce strict constraints (user chose "no relaxations")
        # If relaxations selected, allow violations (user chose "best-effort with relaxations")
        if not selected_suggestions:
            emit("\n⚠️  Hiç esnetme seçilmedi - orijinal kısıtlarla strict mode deneniyor")
            emit("   Not: Eğer strict mode başarısız olursa, plan oluşturulamayacak")
            current_cfg = original_cfg.copy()
            # Use on_decision=None to enforce strict constraints - no violations allowed
            on_decision_for_plan = None
        else:
            emit("\n✓ Seçili esnetmeler uygulanıyor - best-effort mode")
            # Use on_decision=lambda msg: True to allow violations when relaxations are applied
            on_decision_for_plan = lambda msg: True
        
        result = run_planner(
            excel_path=excel_path,
            start_day=start_day,
            num_days=num_days,
            mode_front=mode_front,
            mode_back=mode_back,
            on_progress=on_progress,
            on_decision=on_decision_for_plan,  # Strict if no relaxations, best-effort if relaxations selected
            config_override=current_cfg,
        )
        
        if result["success"]:
            emit("\n✓ Best-effort mode succeeded - plan generated with relaxations")
            result["relaxations_applied"] = _dedupe_relaxations(applied_relaxations)
        else:
            emit("\n❌ Best-effort mode also failed - cannot generate plan")
            result["relaxations_applied"] = _dedupe_relaxations(applied_relaxations)
        
        result["preferred_first_report"] = preferred_report
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = f"Hata oluştu: {str(e)}\n{traceback.format_exc()}"
        emit(error_msg)
        return {
            "success": False,
            "summary_text": error_msg,
            "error": str(e),
            "relaxations_applied": [],
            "preferred_first_report": preferred_report,
        }


def run_planner(
    excel_path: str,
    start_day: str,
    num_days: int,
    mode_front: str = "Her ikisi",
    mode_back: str = "Her ikisi",
    on_progress=None,
    on_decision=None,
    config_override=None,
    relaxations_applied=None,
) -> dict:
    """
    Runs the Instagram post planning logic and returns a summary dict.
    
    Args:
        excel_path: Path to the stock Excel file (stokdosya.xlsx)
        start_day: Starting day name in Turkish (e.g., "Pazartesi")
        num_days: Number of days to plan (1-7)
        mode_front: Front product seasonal mode: "Yazlık", "Kışlık", or "Her ikisi"
        mode_back: Back product seasonal mode: "Yazlık", "Kışlık", or "Her ikisi"
        on_progress: Optional callback function(message: str) for progress updates
        on_decision: Optional callback function(message: str) -> bool for user decisions
        config_override: Optional dict to override default config (for comprehensive GUI)
    
    Returns:
        dict with keys:
            - success: bool (True if plan was created successfully)
            - summary_text: str (summary of the plan or error message)
            - output_excel: str (path to Excel output file, if success)
            - output_md: str (path to Markdown output file, if success)
            - error: str (error message, if not success)
    """
    
    def emit(msg: str):
        """Helper to print and call on_progress callback"""
        print(msg)
        if on_progress:
            on_progress(msg)
    
    def decide(msg: str) -> bool:
        """Helper to handle decision prompts"""
        if on_decision:
            return on_decision(msg)
        # In GUI mode (on_decision is None), we should not use CLI prompts
        # Instead, return False to let the strict pass fail and show the relaxation dialog
        # This function should only be called when on_decision is provided
        emit(f"\n⚠️  Uyarı: {msg}")
        emit("   Strict mode'da devam edilemiyor - relaxation dialog gösterilecek")
        return False
    
    try:
        emit("=" * 70)
        emit("INSTAGRAM WEEKLY POST PLANNER")
        emit("=" * 70)
        
        if config_override:
            cfg = config_override.copy()
        else:
            cfg = DEFAULT_CFG.copy()
            cfg["stock_excel_path"] = excel_path
            cfg["plan_start_day_name"] = start_day
            cfg["plan_num_days"] = num_days
            
            if mode_front == "Yazlık":
                cfg["use_yazlik_front"] = True
                cfg["use_kislik_front"] = False
            elif mode_front == "Kışlık":
                cfg["use_yazlik_front"] = False
                cfg["use_kislik_front"] = True
            else:
                cfg["use_yazlik_front"] = True
                cfg["use_kislik_front"] = True
            
            if mode_back == "Yazlık":
                cfg["use_yazlik_back"] = True
                cfg["use_kislik_back"] = False
            elif mode_back == "Kışlık":
                cfg["use_yazlik_back"] = False
                cfg["use_kislik_back"] = True
            else:
                cfg["use_yazlik_back"] = True
                cfg["use_kislik_back"] = True
        
        emit(f"\nPlan: {start_day} başlangıçlı, {num_days} günlük olarak ayarlandı.")
        if not config_override:
            emit(f"Front mod: {mode_front}, Back mod: {mode_back}\n")
        
        emit("Stok verisi yükleniyor...")
        raw_df = load_stock_data(cfg)
        
        emit("Unique ürünler oluşturuluyor...")
        unique_products = build_unique_products(raw_df)
        
        emit("Takvim oluşturuluyor...")
        calendar = build_post_calendar(cfg)
        
        preferred_products = cfg.get("preferred_first_products", [])
        emit(f"\n📋 Preferred FIRST products loaded: {len(preferred_products)} items")
        if preferred_products:
            for i, pref in enumerate(preferred_products[:5], 1):
                kisakodrenk = pref.get("kisakodrenk", "")
                gun = pref.get("gun", "")
                time = pref.get("time", "")
                emit(f"   {i}. {kisakodrenk} - {gun} {time if time else '(herhangi bir saat)'}")
            if len(preferred_products) > 5:
                emit(f"   ... ve {len(preferred_products) - 5} daha")
        
        if config_override and "preferred_first_products" in config_override:
            from config import PlanConfig
            temp_config = PlanConfig(**config_override)
            pref_errors = temp_config.validate_preferred_products_advanced(calendar)
            if pref_errors:
                error_msg = "Tercihli FIRST ürün doğrulama hataları:\n" + "\n".join(pref_errors)
                emit(error_msg)
                return {
                    "success": False,
                    "summary_text": error_msg,
                    "error": "Preferred FIRST products validation failed"
                }
        
        emit("FIRST ürün havuzu filtreleniyor...")
        cfg_with_calendar = cfg.copy()
        cfg_with_calendar["_calendar_for_pool"] = calendar
        first_candidates = filter_first_products(unique_products, cfg_with_calendar)
        
        # Havuza eklenen tercihli ürünleri havuza ekle (kriterlere uygun olsun ya da olmasın)
        preferred_in_pool = cfg.get("preferred_products_in_pool", [])
        if preferred_in_pool:
            emit(f"Havuza eklenen {len(preferred_in_pool)} tercihli ürün havuza ekleniyor...")
            for kisakodrenk in preferred_in_pool:
                matching = unique_products[
                    unique_products["kisakodrenk"].str.upper().str.strip() == kisakodrenk.upper().strip()
                ]
                if not matching.empty:
                    product = matching.iloc[0]
                    # Ürün zaten havuzda mı kontrol et (normalize edilmiş karşılaştırma)
                    # ÖNEMLİ: Normalize et (İ -> I dahil)
                    kisakodrenk_normalized = (
                        kisakodrenk.upper().strip().replace("İ", "I")
                    )
                    first_candidates_normalized = (
                        first_candidates["kisakodrenk"]
                        .str.upper()
                        .str.strip()
                        .str.replace("İ", "I")
                    )
                    
                    if kisakodrenk_normalized not in first_candidates_normalized.values:
                        # Havuza ekle
                        first_candidates = pd.concat([first_candidates, matching], ignore_index=True)
                        # ÖNEMLİ: Deduplication after concat
                        before_dedup = len(first_candidates)
                        first_candidates = first_candidates.drop_duplicates(subset=["kisakodrenk"]).reset_index(drop=True)
                        after_dedup = len(first_candidates)
                        if before_dedup != after_dedup:
                            emit(f"  ⚠️ Deduplication: {before_dedup} → {after_dedup} (çıkan: {before_dedup - after_dedup})")
                        emit(f"  ✓ {kisakodrenk} havuza eklendi (kriterler atlandı)")
                    else:
                        emit(f"  ℹ {kisakodrenk} zaten havuzda")
                else:
                    emit(f"  ⚠ {kisakodrenk} stok dosyasında bulunamadı")
        
        emit("BACK ürün havuzu filtreleniyor...")
        back_candidates = filter_back_products(unique_products, cfg_with_calendar)
        
        emit("Kısıt analizi yapılıyor...")
        if not run_constraint_analyzer(calendar, first_candidates, back_candidates, cfg, unique_products, decide=decide):
            return {
                "success": False,
                "summary_text": "Plan üretimi iptal edildi (kısıt analizi başarısız).",
                "error": "Constraint analysis failed or user aborted"
            }
        
        emit("FIRST ürünler atanıyor...")
        posts = assign_first_products(calendar, first_candidates, cfg, decide=decide)
        if not posts:
            return {
                "success": False,
                "summary_text": "Hiç FIRST ürün atanamadı, plan oluşturulamadı.",
                "error": "No FIRST products could be assigned"
            }
        
        if preferred_products:
            emit(f"\n📋 Preferred FIRST products placement check:")
            all_stock_kisakodrenk = set(unique_products["kisakodrenk"].str.upper())
            first_pool_kisakodrenk = set(first_candidates["kisakodrenk"].str.upper())
            placed_kisakodrenk = set(p["first_product"]["kisakodrenk"].upper() for p in posts if p.get("first_product"))
            
            preferred_warnings = []
            for i, pref in enumerate(preferred_products, 1):
                kisakodrenk = pref.get("kisakodrenk", "").strip().upper()
                if not kisakodrenk:
                    continue
                
                pref_gun = pref.get("gun", "")
                pref_time = pref.get("time", "")
                pref_info = f"{kisakodrenk}" + (f" (Talep: {pref_gun}" + (f" {pref_time}" if pref_time else "") + ")" if pref_gun else "")
                
                if kisakodrenk not in all_stock_kisakodrenk:
                    msg = f"   ❌ {i}. {pref_info}: Stok dosyasında bulunamadı"
                    emit(msg)
                    preferred_warnings.append(msg)
                elif kisakodrenk not in first_pool_kisakodrenk:
                    msg = f"   ⚠️  {i}. {pref_info}: FIRST havuzuna giremedi (sezon/çekim/stok filtreleri)"
                    emit(msg)
                    preferred_warnings.append(msg)
                elif kisakodrenk in placed_kisakodrenk:
                    emit(f"   ✓ {i}. {pref_info}: Plana atandı")
                else:
                    msg = f"   ⚠️  {i}. {pref_info}: Havuzda ama atama aşamasında yer bulamadı (günlük kısıtlar)"
                    emit(msg)
                    preferred_warnings.append(msg)
            
            if preferred_warnings:
                warning_text = "\n".join(preferred_warnings)
                emit(f"\n⚠️  UYARI: {len(preferred_warnings)} tercihli FIRST ürün atanamadı:\n{warning_text}")
            emit("")
        
        emit("Gelişmiş FIRST kuralları kontrol ediliyor...")
        if not check_advanced_first_constraints(posts, cfg, decide=decide):
            return {
                "success": False,
                "summary_text": "Plan üretimi iptal edildi (Gelişmiş FIRST kuralları karşılanamadı).",
                "error": "Advanced FIRST constraints not met or user aborted"
            }
        
        emit("NOS/DVM kontrolü yapılıyor...")
        if not check_weekly_nos_dvm(posts, cfg, first_candidates, calendar, back_candidates, unique_products, decide=decide):
            return {
                "success": False,
                "summary_text": "Plan üretimi iptal edildi (NOS/DVM kuralları karşılanamadı).",
                "error": "NOS/DVM requirements not met or user aborted"
            }
        
        emit("BACK ürünler atanıyor...")
        posts = assign_back_products(posts, back_candidates, cfg)
        
        emit("Plan doğrulaması yapılıyor...")
        try:
            from validator import validate_plan
            validation_results, validation_summary, validation_df = validate_plan(
                posts, cfg, first_candidates, back_candidates
            )
            emit(validation_summary)
        except Exception as e:
            emit(f"Uyarı: Doğrulama sırasında hata: {e}")
            validation_df = None
        
        emit("Excel çıktısı oluşturuluyor...")
        output_dir = os.path.dirname(os.path.abspath(excel_path))
        output_excel = os.path.join(output_dir, "instagram_haftalik_plan.xlsx")
        output_md = os.path.join(output_dir, "instagram_haftalik_plan.md")
        
        plan_df = export_to_excel(posts, cfg, raw_df, validation_df, relaxations_applied, unique_products)
        
        emit("Markdown çıktısı oluşturuluyor...")
        export_to_markdown(posts, cfg)
        
        summary_lines = []
        summary_lines.append("=" * 70)
        summary_lines.append("PLAN ÖZETİ")
        summary_lines.append("=" * 70)
        
        from collections import Counter
        from instagram_auto_post import TURKISH_DAYS
        
        day_counts = Counter(p["day_name"] for p in posts)
        summary_lines.append("\nGünlük post adetleri:")
        for day in TURKISH_DAYS:
            if day in day_counts:
                summary_lines.append(f"  {day}: {day_counts[day]}")
        
        summary_lines.append(f"\nToplam post sayısı: {len(posts)}")
        
        distinct_first = len({p["first_product"]["kisakodrenk"] for p in posts})
        distinct_back = set()
        for p in posts:
            for bp in p.get("back_products", []):
                distinct_back.add(bp["kisakodrenk"])
        summary_lines.append(f"\nDistinct FIRST ürün adedi: {distinct_first}")
        summary_lines.append(f"Distinct BACK ürün adedi:  {len(distinct_back)}")
        
        nos_first_plan = {
            p["first_product"]["kisakodrenk"]
            for p in posts
            if p["first_product"].get("Nos", "") == "E"
        }
        dvm_first_plan = {
            p["first_product"]["kisakodrenk"]
            for p in posts
            if p["first_product"].get("DVM", "") == "DVM"
        }
        
        summary_lines.append(f"\nPlan içindeki NOS='E' FIRST (distinct): {len(nos_first_plan)} (hedef: {cfg['min_nos_front']})")
        summary_lines.append(f"Plan içindeki DVM='DVM' FIRST (distinct): {len(dvm_first_plan)} (hedef: {cfg['min_dvm_front']})")
        
        summary_lines.append("\n" + "=" * 70)
        summary_lines.append("\n✓ Plan oluşturma tamamlandı!")
        summary_lines.append(f"\nÇıktı dosyaları:")
        summary_lines.append(f"  Excel: {output_excel}")
        summary_lines.append(f"  Markdown: {output_md}")
        
        summary_text = "\n".join(summary_lines)
        emit(summary_text)
        
        return {
            "success": True,
            "summary_text": summary_text,
            "output_excel": output_excel,
            "output_md": output_md,
        }
        
    except Exception as e:
        import traceback
        error_msg = f"Hata oluştu: {str(e)}\n{traceback.format_exc()}"
        emit(error_msg)
        return {
            "success": False,
            "summary_text": error_msg,
            "error": str(e)
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python planner.py <excel_path> [start_day] [num_days] [mode_front] [mode_back]")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    start_day = sys.argv[2] if len(sys.argv) > 2 else "Pazartesi"
    num_days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    mode_front = sys.argv[4] if len(sys.argv) > 4 else "Her ikisi"
    mode_back = sys.argv[5] if len(sys.argv) > 5 else "Her ikisi"
    
    result = run_planner(excel_path, start_day, num_days, mode_front, mode_back)
    
    if not result["success"]:
        sys.exit(1)
