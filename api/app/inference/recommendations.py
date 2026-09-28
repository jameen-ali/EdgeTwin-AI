"""
api/app/inference/recommendations.py — Layer 6 actionable maintenance recommendations.

Generates standardized, domain-grounded maintenance recommendations and action codes
based on:
- Health State & Hardware Trips
- Supervised Failure Risk & Thresholds
- Explainability Top Factors (SHAP feature attribution)
- Physical Sensor Degradation & Out-of-Range Conditions
"""

from __future__ import annotations

from typing import Any

from api.app.inference.schemas import Recommendation

# Standard Action Codes
ACTION_ROUTINE_MONITOR: str = "ACT_ROUTINE_MONITOR"
ACTION_EMERGENCY_INSPECT: str = "ACT_EMERGENCY_INSPECT"
ACTION_REPLACE_TOOL: str = "ACT_REPLACE_TOOL"
ACTION_INSPECT_COOLING: str = "ACT_INSPECT_COOLING"
ACTION_CHECK_ELECTRICAL: str = "ACT_CHECK_ELECTRICAL"
ACTION_CHECK_MECHANICAL_OVERLOAD: str = "ACT_CHECK_MECHANICAL_OVERLOAD"
ACTION_INSPECT_BEARINGS_VIBRATION: str = "ACT_INSPECT_BEARINGS_VIBRATION"
ACTION_CHECK_PRESSURE_SEALS: str = "ACT_CHECK_PRESSURE_SEALS"
ACTION_CALIBRATE_SENSORS: str = "ACT_CALIBRATE_SENSORS"
ACTION_DIAGNOSTIC_AUDIT: str = "ACT_DIAGNOSTIC_AUDIT"
ACTION_CHECK_CONNECTIVITY: str = "ACT_CHECK_CONNECTIVITY"


def generate_recommendation(
    health_state: str,
    *,
    top_factors: list[dict[str, Any]] | None = None,
    hardware_trip: bool = False,
    tool_wear_min: float | None = None,
    out_of_range_count: int = 0,
    missing_count: int = 0,
    failure_probability: float | None = None,
    anomaly_flag: bool | None = None,
) -> Recommendation:
    """Produce a deterministic, explainable Layer 6 maintenance recommendation.

    Parameters
    ----------
    health_state:
        Evaluated Layer 4 health state ("HEALTHY", "WARNING", "CRITICAL",
        "MAINTENANCE_REQUIRED", "OFFLINE").
    top_factors:
        Top contributing SHAP features sorted by absolute magnitude.
    hardware_trip:
        True if edge controller hardware safety limit tripped.
    tool_wear_min:
        Accumulated tool wear in minutes.
    out_of_range_count:
        Number of out-of-range sensor channels.
    missing_count:
        Number of missing sensor channels.
    failure_probability:
        Calibrated failure probability.
    anomaly_flag:
        Unsupervised anomaly detection trigger.

    Returns
    -------
    Recommendation
        Structured recommendation object with action_code, text, urgency, and component.
    """
    p_fail = failure_probability if failure_probability is not None else 0.0

    # 1. Hardware Emergency Safety Trip
    if hardware_trip:
        return Recommendation(
            action_code=ACTION_EMERGENCY_INSPECT,
            recommendation_text=(
                "Hardware safety trip triggered on edge controller. Immediate physical inspection "
                "and root-cause verification required before clearing interlock."
            ),
            urgency="IMMEDIATE",
            target_component="SAFETY_SYSTEM",
            reason="Edge controller safety threshold exceeded.",
        )

    # 2. OFFLINE state
    if health_state == "OFFLINE":
        return Recommendation(
            action_code=ACTION_CHECK_CONNECTIVITY,
            recommendation_text=(
                "Machine is offline or telemetry stream is stale. Verify network connectivity, "
                "gateway status, and edge power supply."
            ),
            urgency="LOW",
            target_component="COMMUNICATIONS",
            reason="Telemetry timeout or broker disconnection.",
        )

    # 3. Tool Wear Maintenance Override
    wear_exceeded = tool_wear_min is not None and tool_wear_min >= 240.0
    if health_state == "MAINTENANCE_REQUIRED" or wear_exceeded:
        wear_str = f"{tool_wear_min:.1f} min" if tool_wear_min is not None else ">= 240 min"
        return Recommendation(
            action_code=ACTION_REPLACE_TOOL,
            recommendation_text=(
                f"Cutting tool wear limit exceeded ({wear_str} >= 240 min). Replace cutting tool "
                "insert and reset tool wear counter."
            ),
            urgency="HIGH" if p_fail >= 0.80 else "MEDIUM",
            target_component="TOOLING",
            reason=f"Tool wear threshold reached ({wear_str}).",
        )

    # 4. Severe / Critical or Warning failure risk with SHAP factor guidance
    if health_state in ("CRITICAL", "WARNING") or p_fail >= 0.16:
        urgency = "HIGH" if (health_state == "CRITICAL" or p_fail >= 0.80) else "MEDIUM"

        # Check top SHAP contributing features (looking for positive risk contributors)
        if top_factors:
            for factor in top_factors:
                feat_name = factor.get("feature_name", "")
                shap_val = factor.get("shap_value", 0.0)
                if shap_val <= 0.0:
                    continue  # Only act on features pushing risk UP

                if feat_name in ("Process_Temperature_C", "Delta_T_C", "Air_Temperature_C"):
                    return Recommendation(
                        action_code=ACTION_INSPECT_COOLING,
                        recommendation_text=(
                            "Elevated process temperature differential detected. Inspect heat "
                            "dissipation system, cooling fluid flow, and heat exchanger fins."
                        ),
                        urgency=urgency,
                        target_component="THERMAL_COOLING",
                        reason=f"High thermal risk driven by {feat_name} (SHAP={shap_val:+.3f}).",
                    )

                if feat_name in ("Current_A", "Voltage_V", "Apparent_Power_VA"):
                    return Recommendation(
                        action_code=ACTION_CHECK_ELECTRICAL,
                        recommendation_text=(
                            "Electrical power anomaly detected. Inspect supply voltage balance, "
                            "motor phase current draw, and power inverter drive stages."
                        ),
                        urgency=urgency,
                        target_component="ELECTRICAL_SUPPLY",
                        reason=f"Electrical anomaly driven by {feat_name} (SHAP={shap_val:+.3f}).",
                    )

                if feat_name in ("Torque_Nm", "Rotational_Speed_RPM", "Mech_Power_W"):
                    return Recommendation(
                        action_code=ACTION_CHECK_MECHANICAL_OVERLOAD,
                        recommendation_text=(
                            "Mechanical overstrain detected. Verify spindle torque load, feed "
                            "rates, drive coupling alignment, and gearbox lubrication."
                        ),
                        urgency=urgency,
                        target_component="DRIVE_TRAIN",
                        reason=f"Mechanical load anomaly driven by {feat_name} (SHAP={shap_val:+.3f}).",
                    )

                if feat_name == "Vibration_mm_s":
                    return Recommendation(
                        action_code=ACTION_INSPECT_BEARINGS_VIBRATION,
                        recommendation_text=(
                            "High mechanical vibration detected. Inspect rotational bearings, shaft "
                            "runout, dynamic balance, and machine mounting rigidity."
                        ),
                        urgency=urgency,
                        target_component="BEARINGS_ROTORS",
                        reason=f"Vibration anomaly driven by {feat_name} (SHAP={shap_val:+.3f}).",
                    )

                if feat_name == "Pressure_bar":
                    return Recommendation(
                        action_code=ACTION_CHECK_PRESSURE_SEALS,
                        recommendation_text=(
                            "Abnormal system pressure detected. Inspect pressure regulator valves, "
                            "hydraulic lines, and cylinder seals for leakage."
                        ),
                        urgency=urgency,
                        target_component="PRESSURE_HYDRAULICS",
                        reason=f"Pressure deviation driven by {feat_name} (SHAP={shap_val:+.3f}).",
                    )

                if feat_name == "Tool_Wear_Min":
                    return Recommendation(
                        action_code=ACTION_REPLACE_TOOL,
                        recommendation_text=(
                            "Tool wear contributing significantly to failure risk. Inspect cutting "
                            "edge condition and schedule tool replacement."
                        ),
                        urgency=urgency,
                        target_component="TOOLING",
                        reason=f"Tool wear acceleration (SHAP={shap_val:+.3f}).",
                    )

    # 5. Sensor Data Quality / Range Violation
    if out_of_range_count > 0 or missing_count >= 3:
        return Recommendation(
            action_code=ACTION_CALIBRATE_SENSORS,
            recommendation_text=(
                "Degraded telemetry signal quality detected. Inspect sensor wiring integrity, "
                "verify analog transducers, and recalibrate out-of-range sensor channels."
            ),
            urgency="MEDIUM",
            target_component="SENSORS_TELEM",
            reason=f"Data quality degradation: {out_of_range_count} out-of-range, {missing_count} missing.",
        )

    # 6. Unsupervised Anomaly without single dominant factor
    if anomaly_flag:
        return Recommendation(
            action_code=ACTION_DIAGNOSTIC_AUDIT,
            recommendation_text=(
                "Unsupervised anomaly detected across operating parameters. Conduct general "
                "system diagnostic audit to identify unusual operating conditions."
            ),
            urgency="MEDIUM",
            target_component="GENERAL_SYSTEM",
            reason="Unsupervised anomaly detector triggered.",
        )

    # 7. Nominal Healthy State
    return Recommendation(
        action_code=ACTION_ROUTINE_MONITOR,
        recommendation_text=(
            "System operating within nominal parameters. Continue standard scheduled monitoring."
        ),
        urgency="ROUTINE",
        target_component="SYSTEM",
        reason="All health metrics nominal.",
    )
