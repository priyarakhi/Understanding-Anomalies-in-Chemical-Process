"""
Reviewed findings for Question 1 ("What changes in the sensors?").

These texts were written by inspecting the event plots on the Question 1 page
(all 11 sensors, 10 min before to 10 min after every event) and checking the
numbers against the raw CSV files. They are interpretations of the plots,
not output of an algorithm. Numbers are rounded. 'Possible reason' lines are
physical explanations offered for discussion; the dataset itself does not
state the cause of the sensor reactions.

Re-check every statement in the dashboard before presenting it.
"""

FINDINGS = [
    dict(
        op="OP10", unit="OP010TA001A001",
        what="Nitrogen injected into the reboiler V001 (5 NL/h via valve HV009), 16:20:00-16:37:00.",
        sensors="T705, T712 (clear); PY23 (pattern change); FT703, FT704, PDI702 (short dip when the injection stops)",
        change="T705 and T712 step down by about 0.25 °C within about one minute (T705: 67.35 -> 67.08 °C; "
               "T712: 67.24 -> 67.01 °C) and stay low while nitrogen flows. PY23 keeps the same average "
               "(about 599 mbar) but its saw-tooth control cycle becomes faster: about 36 cycles per 10 min "
               "during the injection versus about 22-23 before and after.",
        recovery="Yes. T705 is back above 67.25 °C at 16:38:22, about 1.5 min after the injection stops; "
                 "the PY23 cycle returns to its earlier rhythm.",
        note="Only T712 is annotated. The change is small compared with the slow drift of the batch, so the "
             "automatic screening misses it; the plot shows it clearly. Possible reason: the inert gas "
             "has to be removed by the vacuum system, so the pressure controller acts more often."),
    dict(
        op="OP17", unit="OP017TA001A001 - A004",
        what="Four sample withdrawals from the reflux line with a syringe at HV004 (loss of 8.3, 8.5, 31.0 and 39.6 g distillate).",
        sensors="FT704 (clear, annotated); T709, T711, T703 (clear, delayed); T712, T705 (only in A002)",
        change="Reflux flow FT704 falls from about 0.5 to near 0 (A001) or about 0.15 (A003), or switches "
               "repeatedly between 0 and normal (A002, A004) while the syringe is in use. About 2.5-4.5 min "
               "after the onset the column temperatures rise: T709 by 0.7-2.5 °C, T711 by up to 2.5 °C (A002) and 1.4 °C (A004). "
               "The reboiler temperature T703 steps up by 0.15-1.4 °C.",
        recovery="Partly. FT704 recovers as soon as the withdrawal ends. T711 returns to its level. T709 falls "
                 "back but stays above its earlier level in A002 and A004. The step in T703 does not go back "
                 "(no return within 10 min after the annotated end).",
        note="The size of the temperature response does not simply follow the amount withdrawn "
             "(the 8.5 g withdrawal A002 gives the largest T711 rise). Possible reason for the lasting T703 "
             "step: liquid removed from the system changes the composition in the reboiler."),
    dict(
        op="OP18", unit="OP018TA001A001 - A003",
        what="Nitrogen injected below column section C001 via HV001 (50, 30, 30 NL/h for 5.5, 4 and 3 min).",
        sensors="T705, T711, T712, T709 (clear, annotated: T709); PDI702, FT703, FT704 (smaller); PDI701, PY23 (small)",
        change="The column temperatures fall sharply within about 30 s: T705, T711 and T712 by 1.5-2.0 °C, "
               "T709 by 2.8-3.4 °C (A002, A003). In A001 (largest flow, 50 NL/h) T709 instead rises: by about "
               "2 °C at the start and to about 3.5 °C above its earlier level after the injection. PDI702 "
               "swings, and the flows show a small rise followed by a dip when the injection stops.",
        recovery="Yes for T705, T711, T712: back to the previous level about 1 min after the injection stops. "
                 "T709 recovers in A002 and A003, but in A001 it stays higher (no return within 10 min).",
        note="Nitrogen enters at the bottom of the column, and all column temperatures react almost at the same "
             "moment. The reboiler temperature T703 hardly changes."),
    dict(
        op="OP22", unit="OP022TA001A001 and A003",
        what="Sample withdrawals from the reflux line at HV004 (8.2 g and 8.0 g).",
        sensors="FT704, PDI702 (clear); T709 (clear, delayed); FT703, T703 (small)",
        change="PDI702 falls from about 2 to near 0 during the withdrawal and then overshoots above 2; FT704 dips "
               "by about 0.45. T709 rises by 1.1-1.5 °C, peaking about 5-6.5 min after the onset.",
        recovery="Yes for FT704 and PDI702 (within about 2-3 min). T709 decays slowly: in A001 it is back about "
                 "6.5 min after the annotated end; in A003 the recording ends 6.7 min after the event, before "
                 "T709 is back.",
        note="Same kind of disturbance as OP17, but here the buffer-vessel signal PDI702 reacts strongly."),
    dict(
        op="OP22", unit="OP022TA001A002",
        what="Air entering the reflux line through a leaking syringe connection at HV004, 12:15:00-12:20:15.",
        sensors="PDI702 (clear, annotated); FT703, FT704 (clear); T709 (clear); PY23 (small)",
        change="PDI702 jumps from about 2 to about 6 mbar at the start and again near the end. FT703 rises by "
               "about 0.19, FT704 becomes spiky. T709 first dips and then rises.",
        recovery="Yes. PDI702 and the flows return to their normal pattern within about 1-2 min after the leak "
                 "stops; T709 needs about 6 min longer.",
        note="The annotation describes the effect as 'elevated downstream pressure (after the column)'."),
    dict(
        op="OP29", unit="OP029TA001A001",
        what="Five setpoint changes at the same time, 14:06:18-14:17:16: main heater power 210 -> 157.5 W, two wall-heater "
             "setpoints -5 °C, distillate pump P702 off, pressure setpoint 550 -> 500 mbar, PDI702 setpoint 2 -> 1 mbar.",
        sensors="All except FYI702: PY23, FT703, FT704, PDI701, PDI702, T703, T705, T709, T711, T712",
        change="PY23 drops from about 549 to as low as 482 mbar. FT703 falls to about 0 (pump off). FT704 surges "
               "briefly. PDI702 spikes to about 6 and then settles near 1 (its new setpoint). PDI701 halves "
               "(about 1.0 -> 0.5). All temperatures fall: T709 by about 8 °C, T703 by about 4 °C, "
               "T705/T711/T712 by about 3 °C.",
        recovery="Mostly yes, but slowly: flows and PDI702 recover soon after 14:17; pressure and temperatures climb "
                 "back over roughly 10-20 min. Afterwards PY23 and the top temperatures keep oscillating until "
                 "about 15:05 (annotated as A004-A007, 'jumpy heater power', on heater sensors outside the 11).",
        note="This is the only event where almost every sensor reacts, because several settings were changed "
             "at once. Lower pressure lowers boiling temperatures, which fits the temperature drop."),
    dict(
        op="OP29", unit="OP029TA001A002 (4 intervals) and A003",
        what="Class 'Anomaly' (not 'ConfirmedAnomaly'): overshooting response of the pressure controller (TV1), "
             "15:25-15:53, and 11 s at the very end of the recording.",
        sensors="PY23 (annotated); FT703, FT704, PDI702, T703, T705, T709 move together with it",
        change="PY23 drops suddenly by about 40-50 mbar and then climbs back slowly over about 5 min "
               "(large saw-tooth). Each drop is accompanied by a surge in FT703, FT704 and PDI702 and dips in "
               "several temperatures. In the last 11 s of the recording (A003) PDI701 jumps from about 1 to "
               "5.3 and PY23 falls from about 554 to 504 mbar.",
        recovery="Each cycle recovers within minutes, but the pattern repeats. Similar drops also occur just "
                 "outside the annotated intervals (for example around 15:17). A003 cannot be judged because "
                 "the recording ends.",
        note="T711 and T712 rise strongly during 15:25-15:50 while T703 keeps rising. This looks like the late "
             "phase of the batch (T711 rises in the same way at the end of the normal run), not a reaction to "
             "the pressure overshoots."),
    dict(
        op="OP31", unit="OP031TA001A001 and A002",
        what="Cooling-water thermostat TCU1 switched off for 6 min (10:23:45) and 10 min (11:12:00).",
        sensors="FYI702 (clear, annotated); after cooling returns: PY23, FT703, FT704, PDI702, T705, T711, T712",
        change="FYI702 reads exactly 0 from 2-4 s after switch-off (361 s and 599 s of zeros). Little else "
               "changes while the cooling is off. Right after cooling returns, PY23 drops by about 10 mbar (A001) "
               "and 18 mbar (A002), the flows FT703 and FT704 surge and then dip, PDI702 swings, and T705, T711, "
               "T712 dip by a few tenths of a degree (T705: about 0.3 °C in A001, 0.5 °C in A002).",
        recovery="Yes, all signals are back to normal within about 4-7 min after cooling returns, inside the "
                 "annotated interval.",
        note="Most of the visible effect comes AFTER the disturbance ends, which a detector must be able to handle."),
    dict(
        op="OP17, OP18, OP22", unit="Recurrent / permanent spikes (OP017TA001A005, OP018TA001A004, OP022TA001A004)",
        what="Improperly sealed sample valves HV004/HV005: air leaks in during (almost) the whole run.",
        sensors="FT703 and FT704 only",
        change="Short spikes in the mass-flow signals. Inside the annotated spike intervals FT703 is about 7 times "
               "'jumpier' than outside them; FT704 2-8 times. For all other sensors the ratio is between about 0.6 and 1.3, i.e. no clear increase.",
        recovery="Not applicable: the spikes come and go during the whole run (category recurrent/permanent).",
        note="Flow spikes of similar size also appear in the NORMAL runs of OP17, OP18 and OP22, which have no "
             "annotations. In OP22 the whole anomalous run is labelled anomalous (permanent)."),
]
