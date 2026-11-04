"""Build data/metric_templates.json and docs/metric-templates.md from one source.

The metric catalogue, the six evaluation templates and the fictional-data
extensions are defined once, in this file; the JSON and the doc are generated
from it, so they cannot drift apart. Edit this script, not the two outputs.

    python scripts/build_metric_templates.py           # check, then write both files
    python scripts/build_metric_templates.py --check   # exit 1 if either file is out of date

Before writing, it checks the catalogue against the app: the 13 metrics that
may be an action's primary metric must equal lifecycle.METRICS, every `moves`
tag of the 72 plan templates must be a catalogue metric, and every metric a
template or the core set names must exist.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECK_ONLY = "--check" in sys.argv[1:]
sys.path.insert(0, str(REPO))
import lifecycle  # noqa: E402

PLANS = {p["id"]: p for p in json.loads((REPO / "data/plan_templates.json").read_text(encoding="utf-8"))["plans"]}

CLASSES = {
    "outcome": "The verdict — the only class that decides anything",
    "driver": "Explains the outcome",
    "efficiency": "Cost of the result",
    "diagnostic": "Helps find causes; never a result",
    "guardrail": "Stops destructive optimisation — margin % and refund rate only (decided 2 November)",
    "quality_risk": "Watches the system itself: data, automations, agents",
}
DISCIPLINES = ["shared", "ecommerce", "digital_marketing", "performance_marketing",
               "digital_growth", "agentic_ai", "automations"]
DISC_TITLE = {
    "shared": "Shared — outcome, Growth P&L and guardrails (PDF T1)",
    "ecommerce": "Ecommerce (PDF 01)",
    "digital_marketing": "Digital marketing and CRM (PDF 02)",
    "performance_marketing": "Performance marketing (PDF 04)",
    "digital_growth": "Digital growth (PDF 03)",
    "agentic_ai": "Agentic AI (PDF 05)",
    "automations": "Automations (PDF 06)",
}

METRICS = []


def M(key, name, disc, cls, definition, formula, unit, better, grain, source, status,
      ext=None, primary="no", plans=(), pdf="", note="", fits=None, decision=None):
    METRICS.append({
        "key": key, "name": name, "discipline": disc, "class": cls,
        "definition": definition, "formula": formula, "unit": unit, "better": better,
        "grain": grain, "source": list(source), "status": status, "extension": ext,
        "decision": decision, "primary": primary, "plans": list(plans), "pdf": pdf,
        "note": note, "fits": fits,
    })


# --- shared (T1) -----------------------------------------------------------------
M("contribution", "Incremental contribution", "shared", "outcome",
  "The extra contribution an action or component caused, from the store's own orders.",
  "holdout: (contribution per assigned test customer − per assigned control customer) × test "
  "customers; before/after: contribution in the measurement period − the equal period before. "
  "Order contribution = net revenue − product cost − shipping − payment fee − refunds + restocked "
  "cost; the discount is never subtracted again",
  "eur", "higher", "action period; component month", ["orders", "refunds", "assignments"],
  "built", primary="yes", pdf="T1 Economics — incremental outcome; ROI formula",
  note="Store contribution (Growth P&L) is context, never this figure.")
M("avoided_cost", "Verified avoided cost", "shared", "outcome",
  "Paid spending that genuinely fell — a cancelled service, a smaller invoice.",
  "paid cost before − paid cost after, from invoices, with an evidence note; confidence documented",
  "eur", "higher", "action period; component month",
  ["actions.measured_benefit_eur", "actions.evidence_note", "component_months.measured_benefit_eur"],
  "built", primary="yes", pdf="T1 cost savings; 06 Economic proof — verified cash saved",
  note="Freed hours are never avoided cost.")
M("net_benefit", "Net benefit", "shared", "outcome",
  "What an action earned after everything it cost.",
  "measured benefit − setup cost − setup hours × hourly rate − operating cost − operating hours × "
  "hourly rate", "eur", "higher", "action period", ["actions", "clients.hourly_rate_eur"], "built",
  pdf="T1 ROI formula — numerator", note="Adopt only when net benefit ≥ the action's hurdle.")
M("roi", "ROI (action, full payback)", "shared", "outcome",
  "Net benefit per euro invested in the action.",
  "net benefit ÷ (setup cost + setup hours × rate + operating cost + operating hours × rate)",
  "ratio", "higher", "action period", ["actions", "clients.hourly_rate_eur"], "built",
  pdf="T1 ROI formula", note="Same formula as the PDF. ROAS and MER are never ROI.")
M("system_roi", "System ROI (continuation)", "shared", "outcome",
  "Return of the client's running growth system in a month.",
  "(Σ monthly benefits − Σ monthly operating costs incl. hours × rate) ÷ Σ monthly operating "
  "costs, over running components, each benefit_key once",
  "ratio", "higher", "client·month", ["component_months"], "built",
  pdf="T1 ROI; 'count each saving/cost once'",
  note="Compared with the client's roi_target; setup is not counted again.")
M("setup_payback", "Setup payback", "shared", "outcome",
  "How much of the setup cost the running components have earned back.",
  "cumulative net benefit since each component started ÷ total setup cost",
  "ratio", "higher", "client·month", ["component_months", "actions.setup_cost_eur"], "built",
  pdf="T1 Decision economics — payback")
M("contribution_before_marketing", "Store contribution before marketing", "shared", "driver",
  "Growth P&L line: what the month's orders left after product, delivery and payment costs.",
  "net revenue − refunds − (product cost − restocked cost) − shipping − payment fees",
  "eur", "higher", "client·month", ["orders", "refunds"], "built",
  pdf="T1 contribution before media",
  note="Store health, never an action's benefit; incomplete when a cost is missing.")
M("contribution_after_marketing", "Store contribution after marketing", "shared", "driver",
  "Growth P&L line: store contribution after ad spend.",
  "contribution before marketing − ad spend", "eur", "higher", "client·month",
  ["orders", "refunds", "ad_spend"], "built", pdf="T1 contribution after media",
  note="Store health, never an action's benefit.")
M("margin_pct", "Contribution margin %", "shared", "guardrail",
  "Share of net revenue, after refunds, left as contribution before marketing.",
  "contribution before marketing ÷ (net revenue − refunds) × 100",
  "percent", "higher", "client·month; action window", ["orders", "refunds"], "built",
  primary="yes", pdf="01 Value & cost KPIs — contribution margin",
  note="Breach: more than 2 points below the previous three months' average.")
M("refund_rate", "Refund rate", "shared", "guardrail",
  "Orders refunded in the period per order placed in it.",
  "orders refunded in the period ÷ orders placed in the period × 100",
  "percent", "lower", "client·month; action window", ["orders", "refunds"], "built",
  primary="yes", pdf="01 After purchase — refund rate",
  note="Breach: more than 1 point above the previous three months' average.")

# --- ecommerce (01) --------------------------------------------------------------
M("sessions", "Sessions", "ecommerce", "driver", "Visits to the store, by channel when scoped.",
  "Σ sessions", "count", "higher", "client·month·channel", ["sessions"], "built",
  primary="yes", pdf="01 Funnel KPIs — sessions")
M("orders", "Orders", "ecommerce", "driver", "Orders placed.", "count of orders", "count",
  "higher", "client·month·channel", ["orders"], "built", primary="yes",
  pdf="01 Funnel KPIs — orders")
M("revenue", "Net revenue", "ecommerce", "driver", "Sales after discounts, excluding tax.",
  "Σ net revenue (refunds are their own P&L line)", "eur", "higher", "client·month·channel",
  ["orders.net_revenue_eur"], "built", primary="yes",
  pdf="T1 net sales excluding tax / refunds")
M("conversion", "Conversion rate", "ecommerce", "driver", "Orders per session.",
  "orders ÷ sessions", "ratio", "higher", "client·month·channel", ["orders", "sessions"],
  "built", primary="yes", pdf="01 Funnel KPIs — CVR")
M("average_order_value", "Average order value", "ecommerce", "driver", "Net revenue per order.",
  "net revenue ÷ orders", "eur", "higher", "client·month·channel", ["orders"], "built",
  primary="yes", pdf="T1 / 04 — AOV")
M("contribution_per_session", "Contribution per session", "ecommerce", "driver",
  "Store contribution per visit — the per-visitor rate most ecommerce plans decide on.",
  "contribution before marketing ÷ sessions", "eur", "higher", "client·month",
  ["orders", "refunds", "sessions"], "data_ready", primary="proposed",
  plans=[1, 2, 3, 4, 5, 6, 8, 9, 13, 14, 15, 18, 23, 34, 46, 54, 55],
  pdf="01 Value & cost KPIs — revenue / visitor (contribution form)",
  note="An action's result is still its incremental contribution; this is the store's rate.")
M("discount_rate", "Discount rate", "ecommerce", "diagnostic",
  "Share of gross sales given away as discounts.",
  "Σ discounts ÷ (Σ net revenue + Σ discounts)", "ratio", "lower", "client·month",
  ["orders.discount_eur", "orders.net_revenue_eur"], "data_ready", plans=[3],
  pdf="01 Price & offer — discounts, coupons, thresholds",
  note="A lever, read with margin %; discounts are already inside net revenue.")
M("cost_to_serve_per_order", "Cost to serve per order", "ecommerce", "efficiency",
  "Delivery and payment cost of an average order.",
  "(Σ shipping cost + Σ payment fees) ÷ orders", "eur", "lower", "client·month",
  ["orders.shipping_cost_eur", "orders.payment_fee_eur"], "data_ready", primary="proposed",
  plans=[11], pdf="01 Value & cost KPIs — fulfilment / payment / shipping cost per order")
M("refund_value_rate", "Refund value rate", "ecommerce", "diagnostic",
  "Share of net revenue given back as refunds.",
  "Σ refunds recorded in the period ÷ Σ net revenue", "ratio", "lower", "client·month",
  ["refunds.amount_eur", "orders.net_revenue_eur"], "data_ready", plans=[12],
  pdf="01 After purchase — refund value", note="Shown beside the refund-rate guardrail.")
M("units_per_order", "Units per order", "ecommerce", "driver", "Items in an average order.",
  "Σ units ÷ orders", "ratio", "higher", "client·month", ["orders.units (E4)"], "needs_data",
  "E4", primary="proposed", plans=[1, 8, 9, 46], pdf="01 Funnel KPIs — units / order")
M("add_to_cart_rate", "Add-to-cart rate", "ecommerce", "diagnostic",
  "Sessions in which something was added to the cart.",
  "sessions with an add-to-cart ÷ sessions", "ratio", "higher", "client·month·channel·device",
  ["sessions.add_to_carts (E1)"], "needs_data", "E1", primary="proposed",
  plans=[1, 4, 5, 15, 23, 54, 55], pdf="01 Funnel KPIs — add-to-cart rate")
M("checkout_completion_rate", "Checkout completion rate", "ecommerce", "diagnostic",
  "Checkouts that became orders.", "orders ÷ sessions that started checkout", "ratio",
  "higher", "client·month·device", ["sessions.checkouts_started (E1)", "orders"],
  "needs_data", "E1", primary="proposed", plans=[7],
  pdf="01 Funnel KPIs — checkout start / completion")
M("cart_abandonment_rate", "Cart abandonment rate", "ecommerce", "diagnostic",
  "Carts that never became orders.", "1 − orders ÷ sessions with an add-to-cart", "ratio",
  "lower", "client·month·device", ["sessions.add_to_carts (E1)", "orders"], "needs_data", "E1",
  primary="proposed", plans=[7, 65], pdf="01 Funnel KPIs — cart abandonment")
M("mobile_conversion", "Mobile conversion rate", "ecommerce", "driver", "Orders per mobile session.",
  "mobile orders ÷ mobile sessions", "ratio", "higher", "client·month",
  ["sessions.device (E1)", "orders.device (E1)"], "needs_data", "E1", primary="proposed",
  plans=[6], pdf="01 Experience — mobile UX / performance")
M("avoidable_return_share", "Avoidable return share", "ecommerce", "diagnostic",
  "Refunds the store could have prevented.",
  "refunds with reason damaged, wrong item, not as described or late delivery ÷ all refunds",
  "ratio", "lower", "client·month", ["refunds.reason (E5)"], "needs_data", "E5",
  primary="proposed", plans=[12, 40], pdf="01 After purchase — return reason")

# --- digital marketing and CRM (02) ----------------------------------------------
M("new_customers", "New customers", "digital_marketing", "driver", "First-time buyers.",
  "orders with is_new_customer = 1", "count", "higher", "client·month·channel",
  ["orders.is_new_customer"], "built", primary="yes",
  pdf="02 Lifecycle — first customer; 04 new customers")
M("email_click_rate", "Message click rate", "digital_marketing", "diagnostic",
  "Delivered messages that were clicked.", "clicks ÷ delivered", "ratio", "higher",
  "client·month·stream", ["messages_daily (E3)"], "needs_data", "E3",
  plans=[20, 21, 64, 65, 66], pdf="02 CRM KPIs — click rate",
  note="Engagement only. Email-platform-attributed revenue is never used: the holdout is.")
M("unsubscribe_rate", "Unsubscribe rate", "digital_marketing", "diagnostic",
  "Delivered messages that made the contact opt out.", "unsubscribes ÷ delivered", "ratio",
  "lower", "client·month·stream", ["messages_daily (E3)"], "needs_data", "E3",
  plans=[20, 21, 65, 66], pdf="02 CRM KPIs — unsubscribe; Channel quality — message fatigue",
  note="Watched like a guardrail on message-heavy actions; the two fixed guardrails stay the "
       "only ones that flag a breach (decided 2 November).")
M("messages_per_contact", "Message pressure", "digital_marketing", "diagnostic",
  "Messages each contactable contact received in the month.",
  "Σ delivered in the month ÷ contactable contacts", "ratio", "neither", "client·month",
  ["messages_daily (E3)"], "needs_data", "E3", plans=[20, 66],
  pdf="02 Channel quality — message pressure / fatigue",
  note="Too high drives unsubscribes; too low leaves the list unused.")
M("delivery_rate", "Delivery rate", "digital_marketing", "quality_risk",
  "Messages that reached an inbox or a phone.", "delivered ÷ sent", "ratio", "higher",
  "client·month·stream", ["messages_daily (E3)"], "needs_data", "E3", plans=[20, 65, 66],
  pdf="02 CRM KPIs — delivery / bounce; inbox placement")

# --- performance marketing (04) --------------------------------------------------
M("contribution_after_media", "Incremental contribution after media", "performance_marketing",
  "outcome",
  "What a media change earned: the extra contribution in its channel minus the extra spend — "
  "or plus the spend it saved.",
  "incremental contribution of the orders in the action's channel − change in that channel's ad "
  "spend, over the same periods and comparison", "eur", "higher", "action period",
  ["orders.channel", "ad_spend"], "data_ready", plans=[24, 26, 27, 28, 29, 30, 31, 32, 33, 35],
  pdf="04 Measurement — incremental profit; T1 contribution after media",
  note="Not measured today: the app's contribution result ignores ad spend and uses the whole "
       "store — see D1.", decision="D1")
M("ad_spend", "Ad spend", "performance_marketing", "driver", "Paid media cost.", "Σ spend",
  "eur", "neither", "client·month·channel", ["ad_spend"], "built",
  pdf="04 Campaign — budget / spend", note="An input, shown so CPA, CAC and MER can be read.")
M("cpa", "Cost per order (CPA)", "performance_marketing", "efficiency", "Media cost of an order.",
  "ad spend ÷ orders (by channel: channel spend ÷ channel orders)", "eur", "lower",
  "client·month·channel", ["ad_spend", "orders"], "built", primary="yes",
  pdf="04 Delivery to value — CPA")
M("cac", "Customer acquisition cost (CAC)", "performance_marketing", "efficiency",
  "Media cost of a new customer.", "ad spend ÷ new customers", "eur", "lower",
  "client·month·channel", ["ad_spend", "orders.is_new_customer"], "built", primary="yes",
  pdf="04 Measurement — paid CAC",
  note="Paid CAC; blended or fully loaded CAC would add agency and tool costs.")
M("cost_per_session", "Cost per paid session", "performance_marketing", "efficiency",
  "Media cost of a visit from a paid channel.", "channel spend ÷ channel sessions", "eur",
  "lower", "client·month·channel", ["ad_spend", "sessions"], "data_ready", primary="proposed",
  plans=[27, 29, 30, 33], pdf="04 Delivery to value — CPC (landing-session form)",
  note="Stands in for CPC until clicks exist (E2).")
M("cpc", "Cost per click (CPC)", "performance_marketing", "efficiency", "Media cost of a click.",
  "spend ÷ clicks", "eur", "lower", "client·month·channel", ["ad_spend.clicks (E2)"],
  "needs_data", "E2", plans=[27, 29, 30], pdf="04 Delivery to value — CPC")
M("cpm", "Cost per thousand impressions (CPM)", "performance_marketing", "efficiency",
  "Media cost of reach.", "spend ÷ impressions × 1,000", "eur", "lower", "client·month·channel",
  ["ad_spend.impressions (E2)"], "needs_data", "E2", plans=[27, 32],
  pdf="04 Delivery to value — CPM")
M("ctr", "Click-through rate (CTR)", "performance_marketing", "diagnostic",
  "Impressions that were clicked.", "clicks ÷ impressions", "ratio", "higher",
  "client·month·channel", ["ad_spend.clicks", "ad_spend.impressions (E2)"], "needs_data", "E2",
  plans=[27, 32, 33], pdf="04 Delivery to value — CTR",
  note="A creative and feed diagnostic; never a result.")
M("roas", "ROAS", "performance_marketing", "diagnostic", "Store revenue per euro of channel spend.",
  "channel net revenue (store orders) ÷ channel spend", "ratio", "higher", "client·month·channel",
  ["orders", "ad_spend"], "built", pdf="04 Delivery to value — ROAS",
  note="Never ROI (spec §9: the promotion with ROAS 3.0 had ROI −0.17).")
M("break_even_roas", "Break-even ROAS", "performance_marketing", "diagnostic",
  "The ROAS at which a channel's orders only just pay for their own media.",
  "1 ÷ contribution margin before marketing (as a ratio)", "ratio", "neither", "client·month",
  ["orders", "refunds"], "data_ready", plans=[24, 26, 28],
  pdf="T1 Decision economics — break-even CAC / ROAS",
  note="Read beside ROAS: Luna 2.86, Brote 1.67, Roble 4.00 at their profile margins.")
M("mer", "Marketing efficiency ratio (MER)", "performance_marketing", "diagnostic",
  "Store revenue per euro of total ad spend.",
  "net revenue ÷ total ad spend (cost scope: ad spend only)", "ratio", "higher", "client·month",
  ["orders", "ad_spend"], "data_ready", plans=[24, 28],
  pdf="04 Optimisation — MER with defined cost scope", note="MER is not ROI.")
M("new_customer_share", "New-customer share", "performance_marketing", "diagnostic",
  "Share of orders from first-time buyers.",
  "new-customer orders ÷ orders (by channel when scoped)", "ratio", "neither",
  "client·month·channel", ["orders.is_new_customer"], "data_ready", plans=[22, 31],
  pdf="04 Optimisation — new vs existing customer mix",
  note="Plan 31 warns against chasing it: prospecting spend that buys back existing customers is "
       "the waste to find.")
M("platform_overcount", "Platform overcount", "performance_marketing", "quality_risk",
  "How far the ad platform's purchase count exceeds the store's own orders from that channel.",
  "platform-reported purchases ÷ store orders from the channel", "ratio", "lower",
  "client·month·channel", ["ad_spend.platform_purchases (E2)", "orders.channel"], "needs_data",
  "E2", plans=[25, 26, 36],
  pdf="04 Measurement — attribution model / window, cross-channel overlap",
  note="Shows on screen why platform-attributed revenue is never a result.")
M("tracking_capture_rate", "Tracking capture rate", "performance_marketing", "quality_risk",
  "Store orders that the analytics purchase tag recorded.", "tagged purchases ÷ store orders",
  "ratio", "higher", "client·month", ["sessions.tracked_purchases (E1)", "orders"],
  "needs_data", "E1", plans=[25, 37],
  pdf="T2 Reliability — order reconciliation, event deduplication",
  note="Plan 25's acceptance criterion is capture ≥ 98%.")

# --- digital growth (03) ---------------------------------------------------------
M("repeat_rate", "Repeat-purchase rate", "digital_growth", "driver",
  "Customers who bought more than once recently.",
  "customers with two or more orders in the trailing 90 days ÷ customers with one or more",
  "ratio", "higher", "client·month", ["orders.customer_ref"], "built", primary="yes",
  pdf="03 Cohorts — repeat rate")
M("second_order_rate_90d", "Second-order rate within 90 days", "digital_growth", "driver",
  "First-time customers who came back within 90 days.",
  "first-time customers of a month who order again within 90 days ÷ first-time customers of "
  "that month", "ratio", "higher", "first-order cohort month",
  ["orders.customer_ref", "orders.is_new_customer"], "data_ready", primary="proposed",
  plans=[20, 21, 39, 40, 41, 42, 43, 66],
  pdf="03 Cohorts — new / returning; Growth detail — purchase frequency",
  note="A cohort needs 90 days after its month, so the latest three cohorts show as incomplete.",
  fits=["occasional", "monthly"])
M("orders_per_customer", "Orders per customer (180 days)", "digital_growth", "driver",
  "How often a customer buys.", "orders ÷ distinct customers over the trailing 180 days",
  "ratio", "higher", "client·month", ["orders.customer_ref"], "data_ready", primary="proposed",
  plans=[43], pdf="03 Growth detail — purchase frequency", fits=["occasional", "monthly"])
M("days_to_second_order", "Days to second order", "digital_growth", "diagnostic",
  "How long a returning customer took to buy again.",
  "median days between first and second order, for customers with a second order", "days",
  "lower", "first-order cohort month", ["orders.customer_ref", "orders.ordered_at"],
  "data_ready", plans=[41, 43],
  pdf="03 Growth detail — interpurchase time, time to first value",
  fits=["occasional", "monthly"])
M("reactivation_rate", "Reactivation rate", "digital_growth", "driver",
  "Lapsed customers who bought again.",
  "lapsed customers who order in the month ÷ customers lapsed at its start; lapsed = no order "
  "for 180 days (occasional stores) or 60 days (monthly stores)", "ratio", "higher",
  "client·month", ["orders.customer_ref"], "data_ready", primary="proposed", plans=[20, 35],
  pdf="02 Lifecycle — lapsed, reactivated",
  note="Not used for rare-purchase stores such as Roble.", fits=["occasional", "monthly"])
M("cohort_contribution_d90", "Cohort contribution at 90 days", "digital_growth", "driver",
  "What a new customer has actually earned the store in their first 90 days.",
  "contribution of a first-time customer's orders in the 90 days from the first order, averaged "
  "over the cohort", "eur", "higher", "first-order cohort month", ["orders", "refunds"],
  "data_ready", primary="proposed", plans=[21, 39, 40, 42, 43, 48],
  pdf="03 Cohorts — cohort revenue, LTV; T1 revenue- vs contribution-LTV",
  note="Realised, never forecast: LTV forecasting stays out of scope (spec §13).")
M("contribution_to_cac_d90", "90-day contribution to CAC", "digital_growth", "efficiency",
  "Whether a new customer's first 90 days paid back what it cost to acquire them.",
  "cohort contribution at 90 days ÷ CAC of the cohort month", "ratio", "higher",
  "first-order cohort month", ["orders", "refunds", "ad_spend"], "data_ready",
  plans=[22, 24, 28, 31, 44, 48],
  pdf="T1 Decision economics — contribution-LTV:CAC, CAC payback",
  note="Above 1.0, the first 90 days covered paid acquisition.")

# --- agentic AI (05) -------------------------------------------------------------
M("output_acceptance_rate", "Output acceptance rate", "agentic_ai", "quality_risk",
  "Agent outputs a person accepted without a substantive correction.",
  "outputs accepted ÷ outputs reviewed", "ratio", "higher", "component·month",
  ["component_months.outputs", "component_months.outputs_accepted (E6)"], "needs_data", "E6",
  plans=[49, 50, 51, 52, 53, 60],
  pdf="05 Agent KPIs — task success, human acceptance / override")
M("cost_per_accepted_output", "Cost per accepted output", "agentic_ai", "efficiency",
  "What one usable piece of agent work costs, people included.",
  "(operating cost + operating hours × hourly rate) ÷ outputs accepted", "eur", "lower",
  "component·month", ["component_months (E6)", "clients.hourly_rate_eur"], "needs_data", "E6",
  plans=[49, 50, 52, 53, 60], pdf="05 Reliability — cost / successful task",
  note="Plan 60's decision metric.")
M("ai_cost_per_output", "AI cost per output", "agentic_ai", "diagnostic",
  "Model and API cost of one output.", "AI cost ÷ outputs", "eur", "lower", "component·month",
  ["component_months.ai_cost_eur (E6)"], "needs_data", "E6", plans=[60],
  pdf="05 Control — token / API / tool cost")
M("report_correction_rate", "Report correction rate", "agentic_ai", "quality_risk",
  "Sent client reports a reviewer had to correct substantively.",
  "sent reports with was_corrected = 1 ÷ sent reports", "ratio", "lower", "client",
  ["client_reports"], "built", plans=[50], pdf="05 Agent KPIs — human override")
M("report_rejection_rate", "Report rejection rate", "agentic_ai", "quality_risk",
  "Report drafts a reviewer rejected.", "rejected drafts ÷ reviewed drafts", "ratio", "lower",
  "client", ["client_reports"], "built", plans=[50],
  pdf="05 Agent KPIs — accuracy, error rate")
M("cost_per_report_draft", "Cost per report draft", "agentic_ai", "efficiency",
  "Model cost of one report draft.", "Σ generation cost ÷ drafts", "eur", "lower", "client",
  ["client_reports.generation_cost_eur"], "built", plans=[50, 60],
  pdf="05 Agent KPIs — cost / task")

# --- automations (06) ------------------------------------------------------------
M("run_failure_rate", "Run failure rate", "automations", "quality_risk", "Runs that failed.",
  "failed runs ÷ runs", "ratio", "lower", "component·month",
  ["component_months.runs", "component_months.failed_runs"], "data_ready", plans=[70, 71, 72],
  pdf="06 Automation KPIs — runs, success rate",
  note="Runs and failed runs are already shown as counts.")
M("cost_per_run", "Cost per run", "automations", "efficiency", "What one run costs, people included.",
  "(operating cost + operating hours × hourly rate) ÷ runs", "eur", "lower", "component·month",
  ["component_months", "clients.hourly_rate_eur"], "data_ready", plans=[61, 69, 72],
  pdf="06 Automation KPIs — cost / run")
M("exception_rate", "Exception rate", "automations", "quality_risk",
  "Runs a person had to finish by hand.", "exceptions ÷ runs", "ratio", "lower",
  "component·month", ["component_months.exceptions (E6)"], "needs_data", "E6",
  plans=[61, 70, 71, 72], pdf="06 Economic proof — exception / rework rate")
M("hours_freed", "Hours freed (capacity)", "automations", "quality_risk",
  "Staff hours a component freed in the month.", "as recorded on the component month", "hours",
  "higher", "component·month", ["component_months.hours_freed"], "built",
  pdf="06 Automation KPIs — time saved",
  note="Capacity, never money (spec §4) — see 'Where the PDF and the app differ'.")
M("intake_quality", "Intake quality", "automations", "quality_risk",
  "Share of received shop-data batches that were accepted.",
  "accepted ÷ received shop-data batches", "ratio", "higher", "client·month",
  ["automation_events"], "built", pdf="T2 Reliability — completeness; 06 Reliability")
M("duplicate_event_rate", "Duplicate delivery rate", "automations", "quality_risk",
  "Events delivered more than once.", "duplicate events ÷ received events", "ratio", "lower",
  "client·month", ["automation_events.status"], "data_ready",
  pdf="06 Reliability — idempotency key, duplicate-action rate",
  note="A duplicate already changes nothing (external_id); this counts how often it happens.")
M("orders_missing_cost", "Orders with a missing cost", "automations", "quality_risk",
  "Orders whose product, shipping or payment cost did not arrive.",
  "count of orders with any cost missing", "count", "lower", "client·month", ["orders"], "built",
  pdf="T2 Reliability — completeness",
  note="Makes the dependent Growth P&L lines incomplete, never zero.")
M("open_alerts", "Below-target alerts", "automations", "quality_risk",
  "Alerts the below-target automation raised in the month.", "accepted alert events", "count",
  "lower", "client·month", ["automation_events"], "built",
  pdf="06 Operations — anomalies, budget alerts")

# Plans for vocabulary metrics come from the plan templates' own `moves` tags.
for m in METRICS:
    if m["key"] == "contribution":
        m["plans"] = sorted(p for p, t in PLANS.items() if t["benefit_type"] == "contribution")
    elif m["key"] in lifecycle.METRICS:
        m["plans"] = sorted(p for p, t in PLANS.items() if m["key"] in t["moves"])

SCORECARDS = [
    {
        "discipline": "ecommerce",
        "question": "Does the store turn its visits into profitable orders?",
        "decides_on": ["contribution"],
        "comparison": "holdout per visitor or customer where a group can be assigned; otherwise before/after",
        "primary": ["conversion", "average_order_value", "contribution_per_session",
                    "add_to_cart_rate", "checkout_completion_rate", "mobile_conversion",
                    "units_per_order", "cost_to_serve_per_order", "margin_pct", "refund_rate"],
        "driver": ["sessions", "conversion", "average_order_value", "contribution_per_session",
                   "units_per_order", "mobile_conversion"],
        "efficiency": ["cost_to_serve_per_order"],
        "diagnostic": ["add_to_cart_rate", "checkout_completion_rate", "cart_abandonment_rate",
                       "discount_rate", "refund_value_rate", "avoidable_return_share"],
        "quality_risk": ["orders_missing_cost", "tracking_capture_rate"],
        "featured_plan": 3,
        "store_fit": "All three stores. Roble's few orders (about 36 a week at 0.6%) need a longer "
                     "window than Luna's or Brote's before any result means anything.",
    },
    {
        "discipline": "digital_marketing",
        "question": "Does the store earn demand and keep its customers buying, without paying for every visit?",
        "decides_on": ["contribution"],
        "comparison": "holdout per assigned contact for CRM; before/after on the organic channel for SEO and content (observational)",
        "primary": ["new_customers", "repeat_rate", "sessions", "conversion"],
        "driver": ["sessions", "new_customers", "repeat_rate", "conversion"],
        "efficiency": [],
        "diagnostic": ["email_click_rate", "unsubscribe_rate", "messages_per_contact"],
        "quality_risk": ["delivery_rate"],
        "featured_plan": 20,
        "store_fit": "CRM fits Brote (monthly) and Luna (occasional); for Roble (rare purchases) "
                     "the useful levers are search and content. Owned channels have no media "
                     "cost: their cost is the action's own setup and hours.",
    },
    {
        "discipline": "performance_marketing",
        "question": "Does each euro of media buy contribution the store would not have had anyway?",
        "decides_on": ["contribution_after_media"],
        "comparison": "before/after on the action's channel; a matched-region holdout when the plan allows it (plan 36)",
        "primary": ["cpa", "cac", "cost_per_session", "orders", "conversion", "new_customers",
                    "margin_pct"],
        "driver": ["ad_spend", "sessions", "orders", "conversion", "average_order_value"],
        "efficiency": ["cpa", "cac", "cost_per_session", "cpc", "cpm"],
        "diagnostic": ["roas", "break_even_roas", "mer", "new_customer_share", "ctr"],
        "quality_risk": ["platform_overcount", "tracking_capture_rate"],
        "featured_plan": 30,
        "store_fit": "All three stores buy media (8–15% of revenue). Until D1 is decided, the "
                     "result is measured as plain incremental contribution.",
    },
    {
        "discipline": "digital_growth",
        "question": "Do first-time buyers come back, and do the stages after the first order grow?",
        "decides_on": ["contribution"],
        "comparison": "holdout per customer, over the plan's horizon (30–180 days)",
        "primary": ["repeat_rate", "second_order_rate_90d", "orders_per_customer",
                    "reactivation_rate", "cohort_contribution_d90", "new_customers"],
        "driver": ["repeat_rate", "second_order_rate_90d", "orders_per_customer",
                   "reactivation_rate", "cohort_contribution_d90", "new_customers"],
        "efficiency": ["contribution_to_cac_d90"],
        "diagnostic": ["days_to_second_order"],
        "quality_risk": ["orders_missing_cost"],
        "featured_plan": 43,
        "store_fit": "Repeat and reactivation fit Luna (occasional) and Brote (monthly). For "
                     "Roble (rare purchases) growth means new customers and referral, not repeat.",
    },
    {
        "discipline": "agentic_ai",
        "question": "Does the agent produce accepted work for less than it costs, with a person reviewing every output?",
        "decides_on": ["avoided_cost", "contribution"],
        "comparison": "invoice for saved paid work (documented); holdout for shopper-facing assistants (plans 54, 55)",
        "primary": ["avoided_cost", "conversion"],
        "driver": [],
        "efficiency": ["cost_per_accepted_output", "cost_per_report_draft"],
        "diagnostic": ["ai_cost_per_output"],
        "quality_risk": ["output_acceptance_rate", "report_correction_rate",
                         "report_rejection_rate", "run_failure_rate", "hours_freed"],
        "featured_plan": 50,
        "store_fit": "Any store. Agents never calculate ROI or forecast (spec §4); freed hours "
                     "are capacity.",
    },
    {
        "discipline": "automations",
        "question": "Does the workflow run reliably, and does it save paid cost or win contribution?",
        "decides_on": ["avoided_cost", "contribution"],
        "comparison": "invoice for saved paid work; a kept holdout for customer-facing flows (plan 65)",
        "primary": ["avoided_cost", "conversion", "repeat_rate"],
        "driver": ["conversion", "repeat_rate"],
        "efficiency": ["cost_per_run"],
        "diagnostic": ["cart_abandonment_rate", "email_click_rate", "unsubscribe_rate"],
        "quality_risk": ["run_failure_rate", "exception_rate", "intake_quality",
                         "duplicate_event_rate", "orders_missing_cost", "hours_freed",
                         "open_alerts"],
        "featured_plan": 65,
        "store_fit": "Any store; cart recovery needs carts to recover, so it suits Luna and "
                     "Brote more than Roble.",
    },
]

STORES = [("Luna Home", 0.018, 0.35), ("Brote Cosmetics", 0.025, 0.60), ("Roble Muebles", 0.006, 0.25)]
E1 = {"Luna Home": dict(mobile=0.68, views=0.62, atc=0.060, start=0.45, rel=0.60, capture=0.93),
      "Brote Cosmetics": dict(mobile=0.75, views=0.66, atc=0.075, start=0.50, rel=0.75, capture=0.95),
      "Roble Muebles": dict(mobile=0.55, views=0.55, atc=0.025, start=0.40, rel=0.45, capture=0.90)}
for name, conv, _ in STORES:
    p = E1[name]
    p["completion"] = round(conv / (p["atc"] * p["start"]), 3)
    desktop = conv / (p["mobile"] * p["rel"] + 1 - p["mobile"])
    p["desktop_conversion"] = round(desktop, 4)
    p["mobile_conversion"] = round(desktop * p["rel"], 4)
    assert p["completion"] < 1

E2 = {"meta": (0.011, 1.35), "google_shopping": (0.009, 1.15), "instagram": (0.008, 1.40),
      "google_search": (0.050, 1.10), "pinterest": (0.005, 1.50)}
E3 = {"Luna Home": dict(contactable=14000, campaigns="2 a week", click=0.022, unsub=0.0025,
                        flows="welcome; cart recovery (plan 65); post-purchase"),
      "Brote Cosmetics": dict(contactable=6500, campaigns="3 a week", click=0.032, unsub=0.0020,
                              flows="welcome; replenishment; plan 20's segmented campaign"),
      "Roble Muebles": dict(contactable=4000, campaigns="2 a month", click=0.012, unsub=0.0040,
                            flows="welcome")}
E4 = {"Luna Home": 2.2, "Brote Cosmetics": 1.9, "Roble Muebles": 1.15}
REASONS = ["damaged", "wrong_item", "not_as_described", "late_delivery", "changed_mind"]
E5 = {"Luna Home": [0.20, 0.08, 0.20, 0.07, 0.45],
      "Brote Cosmetics": [0.15, 0.10, 0.30, 0.05, 0.40],
      "Roble Muebles": [0.35, 0.05, 0.25, 0.20, 0.15]}
for v in E5.values():
    assert abs(sum(v) - 1) < 1e-9

EXTENSIONS = [
    {"id": "E1", "name": "Funnel steps and device",
     "plain": "What shoppers did on the site before buying — viewed a product, added to the "
              "cart, started checkout — and whether they were on a phone or a computer; plus "
              "how many purchases the analytics tag actually recorded.",
     "adds": ["sessions.device (mobile or desktop), part of the row's key: client · date · channel · device",
              "sessions.product_views, add_to_carts, checkouts_started — sessions that reached each step",
              "sessions.tracked_purchases — purchases the analytics tag recorded",
              "orders.device"],
     "effort": "medium", "changes_intake": True,
     "serves_plans": [4, 5, 6, 7, 23, 25, 34, 37, 54, 55, 65],
     "params": E1},
    {"id": "E2", "name": "Ad delivery and platform-reported purchases",
     "plain": "How many people saw and clicked each channel's ads, and how many purchases the "
              "ad platform claims — always more than the store really received from it.",
     "adds": ["ad_spend.impressions, clicks",
              "ad_spend.platform_purchases, platform_revenue_eur — what the ad platform claims"],
     "effort": "small", "changes_intake": True,
     "serves_plans": [25, 26, 27, 29, 30, 32, 33, 36],
     "params": {"clicks_per_paid_session": 1.15,
                "by_channel": {c: {"ctr": ctr, "platform_purchases_per_store_order": o}
                               for c, (ctr, o) in E2.items()}}},
    {"id": "E3", "name": "Message sends (email and SMS)",
     "plain": "The emails and SMS each store sent — campaigns and automatic flows such as cart "
              "recovery — with how many were delivered, clicked and led to an unsubscribe.",
     "adds": ["new table messages_daily: client · date · channel (email or sms) · stream (a campaign "
              "or flow name) · action_id (nullable) · sent · delivered · clicks · unsubscribes · "
              "contactable (contacts who could receive the stream that day)"],
     "effort": "medium", "changes_intake": True,
     "serves_plans": [20, 21, 40, 41, 64, 65, 66],
     "params": {"delivery_rate": "0.985–0.992", "flow_click_rate": "2–3 × the campaign rate",
                "flow_unsubscribe_rate": 0.0010, "by_store": E3}},
    {"id": "E4", "name": "Units per order",
     "plain": "How many items each order contains, so bundles and cross-selling can be judged.",
     "adds": ["orders.units (≥ 1)"], "effort": "small", "changes_intake": True,
     "serves_plans": [1, 8, 9, 46], "params": {"mean_units": E4, "rule": "1 + Poisson(mean − 1)"}},
    {"id": "E5", "name": "Refund reasons",
     "plain": "Why each refund happened — damaged, wrong item, not as described, late, or the "
              "customer changed their mind — so preventable returns can be told apart.",
     "adds": ["refunds.reason CHECK in (damaged, wrong_item, not_as_described, late_delivery, "
              "changed_mind); all but changed_mind count as avoidable"],
     "effort": "small", "changes_intake": True, "serves_plans": [11, 12, 40],
     "params": {s: dict(zip(REASONS, v)) for s, v in E5.items()}},
    {"id": "E6", "name": "Agent and automation output counts",
     "plain": "For each AI agent and automation, how much work it produced each month, how much "
              "of it a person accepted, how often a person had to step in, and what the AI cost.",
     "adds": ["component_months.outputs, outputs_accepted, exceptions, ai_cost_eur (nullable; "
              "automation and agent components only)"],
     "effort": "small", "changes_intake": False,
     "serves_plans": [49, 50, 51, 52, 53, 60, 61, 69, 70, 71, 72],
     "params": {"Luna analytics agent (plan 50)": "4 outputs a month (weekly report), 3–4 "
                "accepted, no exceptions; AI cost = Σ generation cost of the month's report drafts",
                "Luna cart-recovery flow (plan 65)": "30–31 runs a month (daily); outputs = "
                "messages sent (E3); 0–3 exceptions; no AI cost"}},
]

# The core set: the few metrics the screens and the presentation show for each
# discipline (Carlos, 4 November: "only the most representative"). The rest of
# the catalogue stays as reference. Proposed by Claude Code; change freely.
CORE = {
    "shared": (["roi", "system_roi", "margin_pct", "refund_rate"],
               "The verdict and the two guardrails — shown for every discipline."),
    "ecommerce": (["conversion", "average_order_value", "contribution_per_session"],
                  "How many visits buy, how much they spend, and what each visit earns."),
    "digital_marketing": (["sessions", "new_customers", "email_click_rate"],
                          "Earned traffic, new buyers, and whether owned messages are read."),
    "performance_marketing": (["contribution_after_media", "cac", "roas"],
                              "What media really earned (D1), what a new customer costs, and "
                              "ROAS shown beside them to explain why it is not ROI."),
    "digital_growth": (["repeat_rate", "second_order_rate_90d", "contribution_to_cac_d90"],
                       "Whether customers come back, how soon, and whether the first 90 days "
                       "paid back their acquisition."),
    "agentic_ai": (["output_acceptance_rate", "cost_per_accepted_output",
                    "report_correction_rate"],
                   "How much agent work a person accepts, what it costs, and how often a "
                   "person corrects it."),
    "automations": (["run_failure_rate", "cost_per_run", "intake_quality"],
                    "Whether the workflows run, what a run costs, and whether data arrives "
                    "intact."),
}

# --- validation --------------------------------------------------------------------
keys = [m["key"] for m in METRICS]
assert len(keys) == len(set(keys)), "duplicate key"
by_key = {m["key"]: m for m in METRICS}
for m in METRICS:
    assert m["class"] in CLASSES, m["key"]
    assert m["discipline"] in DISCIPLINES, m["key"]
    assert m["status"] in ("built", "data_ready", "needs_data"), m["key"]
    assert (m["status"] == "needs_data") == (m["extension"] is not None), m["key"]
    assert m["primary"] in ("yes", "proposed", "no"), m["key"]
    assert m["better"] in ("higher", "lower", "neither"), m["key"]
    if m["primary"] == "proposed":
        assert m["better"] != "neither", m["key"]
    assert all(1 <= p <= 72 for p in m["plans"]), m["key"]
    assert m["pdf"], m["key"]
vocab = {m["key"] for m in METRICS if m["primary"] == "yes"}
assert vocab == set(lifecycle.METRICS), (vocab ^ set(lifecycle.METRICS))
moves = {v for t in PLANS.values() for v in t["moves"]}
assert moves <= set(keys), moves - set(keys)
for sc in SCORECARDS:
    for field in ("decides_on", "primary", "driver", "efficiency", "diagnostic", "quality_risk"):
        for k in sc[field]:
            assert k in by_key, (sc["discipline"], k)
    for k in sc["primary"]:
        assert by_key[k]["primary"] in ("yes", "proposed"), k
    assert PLANS[sc["featured_plan"]]["featured"], sc["featured_plan"]
    assert PLANS[sc["featured_plan"]]["discipline"] == sc["discipline"]
for e in EXTENSIONS:
    e["unlocks"] = [m["key"] for m in METRICS if m["extension"] == e["id"]]
    assert e["unlocks"] or e["id"] == "E6", e["id"]
ext_ids = {e["id"] for e in EXTENSIONS}
assert {m["extension"] for m in METRICS if m["extension"]} <= ext_ids
assert set(CORE) == set(DISCIPLINES), set(CORE) ^ set(DISCIPLINES)
core_keys = [k for ks, _ in CORE.values() for k in ks]
assert len(core_keys) == len(set(core_keys)), "a metric is in the core set twice"
for k in core_keys:
    assert k in by_key, k
for m in METRICS:
    m["core"] = m["key"] in core_keys

counts = {s: sum(m["status"] == s for m in METRICS) for s in ("built", "data_ready", "needs_data")}
print("metrics", len(METRICS), counts, "proposed", sum(m["primary"] == "proposed" for m in METRICS))

# --- write the JSON ---------------------------------------------------------------
out = {
    "source": "Unified ROI System — variables, KPIs, levers and objects (A4 summary, 3 pages, "
              "Carlos M. Muñoz Morillas, 4 November 2026; docs/sources/"
              "Unified_ROI_Variables_A4_EN.pdf), selected for ecommerce in "
              "docs/metric-templates.md",
    "status": "proposal, 4 November 2026 — not loaded by the app; D1 decided (yes), D2 and "
              "D3 open — see docs/metric-templates.md",
    "generated_by": "scripts/build_metric_templates.py — edit the script, not this file",
    "classes": CLASSES,
    "status_values": {
        "built": "the app computes it today",
        "data_ready": "the fictional data already holds what it needs; measure.py needs the formula",
        "needs_data": "needs the data extension named in `extension`",
    },
    "primary_values": {
        "yes": "in today's vocabulary (lifecycle.METRICS): an action's primary_metric may name it",
        "proposed": "would join the vocabulary under decision D3",
        "no": "never an action's primary metric",
    },
    "core_set": {d: {"metrics": ks, "why": why} for d, (ks, why) in CORE.items()},
    "metrics": METRICS,
    "scorecards": SCORECARDS,
    "data_extensions": EXTENSIONS,
}
JSON_TEXT = json.dumps(out, ensure_ascii=False, indent=2) + "\n"


# --- write the doc -----------------------------------------------------------------
def tag(k):
    m = by_key[k]
    label = m["name"]
    if m["status"] == "data_ready":
        label += " *(ready)*"
    elif m["status"] == "needs_data":
        label += f" *({m['extension']})*"
    if m["decision"]:
        label += f" *({m['decision']})*"
    return label


def plans_text(m):
    if m["key"] == "contribution":
        return f"all {len(m['plans'])} contribution plans"
    if m["key"] in ("net_benefit", "roi"):
        return "every action"
    return ", ".join(f"{p:02d}" for p in m["plans"]) or "—"


STATUS_TEXT = {"built": "built", "data_ready": "data ready",
               "needs_data": None}
CLASS_TEXT = {"outcome": "Outcome", "driver": "Driver", "efficiency": "Efficiency",
              "diagnostic": "Diagnostic", "guardrail": "Guardrail", "quality_risk": "Quality and risk"}

scorecard_md = []
for sc in SCORECARDS:
    plan = PLANS[sc["featured_plan"]]
    title = DISC_TITLE[sc["discipline"]].split(" (")[0]
    scorecard_md.append(f"### {title}\n")
    scorecard_md.append(f"*{sc['question']}*\n")
    scorecard_md.append(f"- **Decides on:** {' or '.join(tag(k) for k in sc['decides_on'])}")
    scorecard_md.append(f"- **Comparison:** {sc['comparison']}")
    scorecard_md.append(f"- **Featured plan:** {plan['id']:02d} {plan['title']}")
    prim = []
    for k in sc["primary"]:
        prim.append(tag(k) + (" ⁺" if by_key[k]["primary"] == "proposed" else ""))
    scorecard_md.append(f"- **Primary metric options:** {', '.join(prim)}")
    scorecard_md.append(f"- **Store fit:** {sc['store_fit']}\n")
    scorecard_md.append("| Class | Metrics |\n|---|---|")
    for field in ("driver", "efficiency", "diagnostic"):
        if sc[field]:
            scorecard_md.append(f"| {CLASS_TEXT[field]} | {' · '.join(tag(k) for k in sc[field])} |")
    scorecard_md.append("| Guardrail | Contribution margin % · Refund rate |")
    scorecard_md.append(f"| Quality and risk | {' · '.join(tag(k) for k in sc['quality_risk'])} |\n")

catalogue_md = []
for d in DISCIPLINES:
    rows = [m for m in METRICS if m["discipline"] == d]
    catalogue_md.append(f"### {DISC_TITLE[d]}\n")
    catalogue_md.append("| Metric | Class | Formula | Status | Plans |\n|---|---|---|---|---|")
    for m in rows:
        status = STATUS_TEXT[m["status"]] or f"needs {m['extension']}"
        if m["decision"]:
            status += f", {m['decision']}"
        name = f"**{m['name']}** `{m['key']}`" + (" ⁺" if m["primary"] == "proposed" else "")
        formula = m["formula"]
        if m["note"]:
            formula += f". *{m['note']}*"
        catalogue_md.append(f"| {name} | {CLASS_TEXT[m['class']]} | {formula} | {status} | {plans_text(m)} |")
    catalogue_md.append("")

ext_md = ["| | In plain words | Adds to the data | Unlocks | Effort | Changes the intake |",
          "|---|---|---|---|---|---|"]
for e in EXTENSIONS:
    unlocks = ", ".join(f"`{k}`" for k in e["unlocks"])
    ext_md.append(f"| **{e['id']}** {e['name']} | {e['plain']} | {'<br>'.join(e['adds'])} | "
                  f"{unlocks} | {e['effort']} | {'yes' if e['changes_intake'] else 'no'} |")

core_md = ["| Shown for | Core metrics | Why these |", "|---|---|---|"]
for d, (ks, why) in CORE.items():
    core_md.append(f"| {DISC_TITLE[d].split(' (')[0].split(' —')[0]} | "
                   f"{' · '.join(tag(k) for k in ks)} | {why} |")

pct = lambda x: f"{x * 100:.1f}%"  # noqa: E731
pct2 = lambda x: f"{x * 100:.2f}%"  # noqa: E731
e1_md = ["| Store | Conversion (today) | Mobile share of sessions | Product-view sessions | "
         "Add-to-cart sessions | Checkout starts per add-to-cart | Checkout completion (derived) "
         "| Desktop / mobile conversion (derived) | Tag capture |",
         "|---|---|---|---|---|---|---|---|---|"]
for name, conv, _ in STORES:
    p = E1[name]
    e1_md.append(f"| {name} | {pct(conv)} | {pct(p['mobile'])} | {pct(p['views'])} | {pct(p['atc'])} "
                 f"| {pct(p['start'])} | {pct(p['completion'])} | {pct2(p['desktop_conversion'])} / "
                 f"{pct2(p['mobile_conversion'])} | {pct(p['capture'])} |")
e2_md = ["| Channel | CTR | Platform purchases per store order |", "|---|---|---|"]
for c, (ctr, o) in E2.items():
    e2_md.append(f"| `{c}` | {pct(ctr)} | {o:.2f} |")
e3_md = ["| Store | Contactable contacts | Campaigns | Campaign click rate | Campaign unsubscribe rate | Flows |",
         "|---|---|---|---|---|---|"]
for name, p in E3.items():
    e3_md.append(f"| {name} | {p['contactable']:,} | {p['campaigns']} | {pct(p['click'])} | "
                 f"{pct2(p['unsub'])} | {p['flows']} |")
e45_md = ["| Store | Units per order (mean) | Damaged | Wrong item | Not as described | Late delivery "
          "| Changed mind | Avoidable share | Break-even ROAS |", "|---|---|---|---|---|---|---|---|---|"]
for name, _, margin in STORES:
    r = E5[name]
    e45_md.append(f"| {name} | {E4[name]} | " + " | ".join(f"{x * 100:.0f}%" for x in r)
                  + f" | {(1 - r[4]) * 100:.0f}% | {1 / margin:.2f} |")

n = len(METRICS)
TEXT = f"""# Metric templates — what the app evaluates, and the fictional data behind it

**Status:** proposal, 4 November 2026 — branch `docs/metric-templates`. Nothing
here is loaded by the app or produced by the generator yet; the three decisions
at the end say what would change (D1 decided: yes). **Source:** Carlos's
*Unified ROI System — variables, KPIs, levers and objects* (A4 summary, 3 pages,
4 November 2026), read in full and kept in the repository:
[`sources/Unified_ROI_Variables_A4_EN.pdf`](sources/Unified_ROI_Variables_A4_EN.pdf).
The machine-readable twin is
[`data/metric_templates.json`](../data/metric_templates.json). **Both files are
generated** by [`scripts/build_metric_templates.py`](../scripts/build_metric_templates.py),
which also checks the catalogue against the app — edit the script, not the
files; `--check` reports a file that is out of date.

## Why this page exists

The app already measures ROI with 13 metrics (spec v2 §4). The Unified ROI
summary lists several hundred variables across six disciplines and three shared
layers, for B2B and B2C. This page selects from it — as its own page 2 says,
*"Select variables for the business model"* — the metrics an agency advising
three fictional online stores needs to evaluate a project, groups them into one
evaluation template per discipline, and states what fictional data each one
needs.

**The selection rule is the ecommerce test.** A variable becomes a metric
template only if (1) it moves or explains a store KPI or an order's economics,
(2) a small ecommerce team can act on it, and (3) the store's own data — orders,
refunds, sessions, ad spend, messages, the app's own records — can show it.
Everything else is listed under [Left out](#left-out-from-the-pdf), with the
reason.

**Result:** {n} metric templates — {counts['built']} the app computes today,
{counts['data_ready']} whose data already exists (a formula in `measure.py` is
all they need — contribution after media also needs decision D1), and
{counts['needs_data']} that need one of six small fictional data extensions
(E1–E6). **Only a core set of {len(core_keys)} is meant for the screens and the
presentation** — [the core set](#the-core-set); the rest is reference.

## How the PDF maps onto the app

| PDF block | Where it lives in the app |
|---|---|
| 01 Ecommerce | Store drivers, the Growth P&L and funnel diagnostics — the ecommerce template |
| 02 Digital marketing and CRM | Channel sessions, new customers, message metrics — the digital marketing template |
| 03 Digital growth | The growth loop itself (every action) and cohort metrics — the digital growth template |
| 04 Performance marketing | Spend, CPA, CAC; ROAS and MER as diagnostics — the performance template |
| 05 Agentic AI | Agent components and the client report; *Control* is the Week 11 agent checklist |
| 06 Automations | Automation components and intake events; *Reliability* is built as API controls |
| T1 Economics and business | [`roi.py`](../roi.py) and [`measure.py`](../measure.py): contribution, net benefit, ROI |
| T2 Context, data and stack | The client profile, the shop-data tables, this template format (the PDF's *KPI contract*), the quality metrics |
| T3 People, delivery and governance | Users and roles, the approval workflow, `action_history`, the Week 11 policy |

The PDF's **Experiments** record (03) is already the `actions` table: ID → `id`;
objective and hypothesis → `hypothesis`; owner → `owner_id`; funnel stage →
`lifecycle_stage`; audience, control, variants and split → `assignments`;
primary / secondary / guardrail KPI → `primary_metric` plus the two fixed
guardrails; start and end → `window_start`, `window_end`, `post_period_days`;
lift and incremental value → `measured_benefit_eur`; uncertainty →
`confidence`; cost → setup and operating cost and hours; decision → `decision`;
learning → `decision_note`.

## The ROI formula is already the same

The PDF (page 1): *ROI = (incremental contribution before programme costs +
verified savings − programme costs) / programme costs.* Term by term:

| PDF | App (spec v2 §4) |
|---|---|
| Incremental contribution | `measured_benefit_eur` of a `contribution` action — holdout or before/after |
| Verified savings | `measured_benefit_eur` of an `avoided_cost` action — invoice, `documented`, with an evidence note |
| Programme costs | setup cost + operating cost + (setup hours + operating hours) × the client's hourly rate |
| Same period and currency | Euros; the measurement period is the window plus the post-period |
| Count each saving and cost once | `benefit_key`, enforced by a partial unique index |
| ROAS and MER are not ROI | ROAS and MER are diagnostics |
| Released capacity is value only when used or saved | `hours_freed` is capacity, never money — see [differences](#where-the-pdf-and-the-app-differ) |

One difference in practice: an action carries one benefit type, so a project
that both wins contribution and saves a paid cost is recorded as two actions or
components, each evidenced its own way; system ROI then adds them. **One gap:**
for an action that changes media spend, the incremental contribution must be
measured *after media*, and today it is not — see **D1**.

## The template format

From the PDF's *KPI contract* (T2), trimmed to what the app uses. Each metric in
the JSON has: `key` · `name` · `discipline` (its home in the PDF) · `class` (the
spec's six) · `definition` · `formula` · `unit` · `better` (higher, lower or
neither) · `grain` · `source` (tables and fields) · `status` · `extension` ·
`primary` · `plans` (the action plans that move it or decide on it) · `pdf`
(where it comes from) · `note` · `fits` (purchase frequencies it suits, when not
all).

Dropped from the KPI contract: **owner** (an action's owner is enough),
**target** (the only target is the client's ROI target — the app never compares
a store with an invented benchmark), **attribution model and window** (results
come from holdout or before/after, never from attribution), **frequency** and
**currency** (always monthly or the action's period; always euros).

**Status:** built · *ready* — data exists, formula to add · *E1–E6* — needs that
data extension. **⁺** marks a metric *proposed* as a primary metric under D3;
the 13 metrics of today's vocabulary (`lifecycle.METRICS`) keep their place.

## The six evaluation templates

Every template is judged the same way: the **outcome** decides (net benefit
against the hurdle and ROI for a pilot; system ROI and setup payback once
adopted), the store's **Growth P&L** is context and never the result, and every
action is checked on the same **two guardrails**, margin % and refund rate.
What changes by discipline is the primary metric, the drivers that explain the
result, and the diagnostics that help find causes.

{chr(10).join(scorecard_md)}
## The core set

Sixty-five metrics are a reference, not a screen. The dashboards and the Week
12 presentation show only the **core set** below — the most representative
three per discipline, plus the verdict and the two guardrails that every
discipline shares ({len(core_keys)} in all). Proposed on 4 November after Carlos
asked for *"only the most representative"*; it is defined once in the build
script and marked `core` in the JSON, so changing it is a one-line edit.

{chr(10).join(core_md)}

## Metric catalogue

Grouped by home discipline; the templates above borrow across groups. Plans are
the action-plan numbers ([`plan-lever-map.md`](plan-lever-map.md)); for the 13
vocabulary metrics they come from the plans' own `moves` tags.

{chr(10).join(catalogue_md)}
## Fictional data

Today's tables — `orders`, `refunds`, `sessions`, `ad_spend`, `assignments`,
`component_months`, `client_reports`, `automation_events` — already carry
{counts['built'] + counts['data_ready']} of the {n} metrics. Six extensions
carry the other {counts['needs_data']}. All six add columns to existing tables,
except E3, which is one new table.

{chr(10).join(ext_md)}

### Generation settings

These are **settings for the fictional generator, not benchmarks**: the app
never shows them as targets or compares a store with them. Each is chosen so
that the store's existing figures (spec v2 §9) still hold.

**E1 — funnel and device.** Checkout completion and the two device conversions
are derived, so the funnel multiplies back to each store's conversion today.

{chr(10).join(e1_md)}

**E2 — ad delivery.** Clicks = the channel's paid sessions × 1.15 (some clicks
never land); impressions = clicks ÷ CTR; platform purchases = the store's orders
from the channel × the over-count below; platform revenue = platform purchases ×
the store's average order, with noise.

{chr(10).join(e2_md)}

**E3 — messages.** Delivery 98.5–99.2% of sent; flow click rates two to three
times the campaign rate; flow unsubscribes 0.10% of delivered; the contactable
list grows about 1.5% a month.

{chr(10).join(e3_md)}

**E4 and E5 — units and refund reasons** (break-even ROAS shown for reference:
1 ÷ the profile margin).

{chr(10).join(e45_md)}

**E6 — output counts.** Luna's analytics agent (plan 50): 4 outputs a month (the
weekly report), 3–4 accepted, no exceptions, AI cost = the generation cost of
that month's report drafts. Luna's cart-recovery flow (plan 65): 30–31 daily
runs, outputs = messages sent (E3), 0–3 exceptions, no AI cost.

### Rules that keep the data honest

1. **Funnel steps nest on every row:** orders ≤ checkout starts ≤ add-to-carts ≤
   product views ≤ sessions.
2. **Device conversions average back** to the store's conversion, weighted by
   the mobile share.
3. **Platforms over-count:** platform-reported purchases exceed the store's own
   orders from that channel, so the screen can show why platform revenue is
   never a result.
4. **An action's message stream goes to its test group only:** the stream's
   sends equal its test assignments; the control group receives nothing. When E3
   is built, cart recovery (Luna) and plan 20 (Brote) follow this rule.
5. **One source for each figure:** an agent component's AI cost is the sum of
   its report drafts' generation cost, never a second number.
6. **Fixed seed, Luna first** (spec v2 §9 build order), and every client keeps
   `is_fictional = 1`.

## Left out from the PDF

| PDF variables | Why they are not templates |
|---|---|
| 01 Catalogue and PIM (SKU, variant, taxonomy, GTIN); order and stock (stockout rate, safety stock, inventory turnover, sell-through, forecast error, supplier lead time); feed rejection rate | Needs a SKU and stock model the fictional data does not have; plans 10 and 67 are rated *no* |
| 01 Site search (zero-result rate, autocomplete, filters) | Needs site-search logs |
| 01 Fulfilment SLA and on-time rate; support contacts, resolution time, CSAT/NPS; UGC | No fulfilment or support events; refund reasons (E5) carry the part that touches contribution |
| 01 Payments (authorisation and decline rates, chargebacks, fraud, recovered payments) | No payment events |
| 01 Operations (languages, currencies, tax, duties, marketplace fees, price parity) | One country and one currency per store; plan 47 is rated *no* |
| 02 B2B and lead generation (MQL, SQL, pipeline, win rate, sales cycle) | None of the three stores sells B2B; plans 57, 62 and 63 are rated *no* |
| 02 Channels outside the stores' mix (influencers, affiliates, retail media, CTV, app stores, local and offline) | Not in any store's channel mix; plan 22 stays *partial* |
| 02 Channel quality (share of search, brand vs non-brand demand, AI-referral conversions, sender reputation) | Needs search-console or query data |
| 03 Recurring models (MRR, ARR, net revenue retention, trial-to-paid, dunning) and service or booking models | Brote's subscription is generated as repeat orders, which repeat rate and cohorts already measure; the rest is not ecommerce |
| 03 Test design (minimum detectable effect, power, sample-ratio mismatch, stopping rules) | The app labels evidence (`confidence`) but does not compute significance — worth one honest sentence in the Week 12 presentation, especially for Roble's small samples |
| 04 Reach, frequency, impression share, creative fatigue, conversion lag, offline conversion import | Needs user-level or platform-side data |
| 04 Marketing-mix modelling, response curves, saturation, marginal ROI, iROAS | Excluded by spec v2 §13 |
| 05 Agent specification and control (models, tools, permissions, triggers, traces, evaluation sets, groundedness, prompt-injection resistance) | Governance, not store metrics: the Week 11 agent checklist; reports already store model, prompt version and cost |
| 05 The 20-agent catalogue | Only the read-only report agent is built; plans 49–59 stay reference |
| 06 Reliability controls (webhook signature, idempotency key, retries, timeouts, rate limits, queues, rollback, versions) | Controls, not store metrics: signature checks and idempotency are built into the API and tested (spec v2 §8, §11); retries, timeouts and queues live in the Make scenarios and their portfolio write-ups; rate limits are a Week 8 question. The duplicate rate is the one metric kept |
| T1 Decision context (seasonality, price elasticity, competitor price, concentration, scenarios); working capital, cash conversion cycle | No stock, cash or competitor model |
| T2 Records and systems (CDP, PIM, ERP, OMS, WMS, warehouse), lineage, identity match, consent coverage | CDP and warehouse are excluded by spec v2 §13; consent coverage belongs on the Week 11 GDPR page |
| T3 People, delivery and governance | Already the app's workflow and audit history and the Week 11 policy — structure, not metrics |

## Where the PDF and the app differ

1. **Released capacity.** The PDF (page 3): *"Released capacity becomes
   financial value only when actually used or saved."* The app never turns
   `hours_freed` into money. I kept the app's rule and read the PDF's line
   through it: *saved* means a paid cost fell (an `invoice` result), and *used*
   means the freed time produced its own measured result in another action,
   valued there. The hours themselves are never priced.
2. **Guardrails.** The PDF treats *guardrail* as a type any KPI can have; the
   app has two fixed guardrails (decided 2 November). Unsubscribe rate and
   similar watch-metrics are diagnostics here.
3. **B2B + B2C.** The PDF covers both; the app's three stores are B2C (two
   direct-to-consumer, one subscription), so the B2B variables are left out.
4. **Contribution-LTV.** The PDF lists contribution-LTV; the app has no
   forecasting (spec v2 §13), so the templates use *realised* cohort
   contribution at 90 days and its ratio to CAC.

## Decisions

**D1 — Measure media actions after media, in their channel.** ✅ *Decided 4
November: yes — implemented in its own pull request (schema, `measure.py`,
spec, tests).* Until then, an action's
contribution result ([`measure.py`](../measure.py), `contribution_between` and
`before_after_benefit`) never subtracts ad spend and always compares the whole
store, although spec v2 §4 says before/after is *"for the action's scope"* and
no scope field exists. So for a media action the result is wrong in both
directions: Roble's search-term pilot (plan 30, in progress), whose whole point
is the media it saves, would show that saving as zero, and an action that adds
spend would look better than it is unless the spend were typed in as operating
cost. Ten plans decide on contribution after media (24, 26–33, 35).
*Recommendation:* add a nullable `scope_channel` to `actions`; when it is set,
the before/after result uses that channel's orders and subtracts the change in
that channel's ad spend. Whole-store actions (scope empty) are unchanged. One
spec paragraph, one formula, one test.

**D2 — Which data extensions to build.** ❓ The six extensions, in plain words,
are in the [Fictional data](#fictional-data) table. *Recommendation (revised 4
November, after the course's "judgement over volume" rule):* build **E2, E4 and
E5** — a few columns each — before the Week 5 intake; add **E1** only if time
allows (it changes the sessions key); **park E3 and E6** (a new table, and
monthly counts typed by the team). The core set needs E3 only for its
message click rate and E6 for its two agent metrics, which stay *reference*
until those are built. **Timing:** E1, E2, E4 and E5
change the rows the shop-data intake accepts, and the intake automation
(automation 2 since the 4 November re-map) is built in Week 5 — so decide each
of them before it is built: build it into the intake from the start, or leave
it out, rather than change the intake afterwards. E3 adds a new kind of row.

**D3 — Load the catalogue into the app.** ❓ *Recommendation:* after D2, load
`data/metric_templates.json` as read-only reference (like the plan templates),
let an action's primary metric be any metric marked ⁺, and let *where to grow*
check every driver and efficiency metric whose data exists — so a weak
add-to-cart rate points at plans such as 04, 05 and 23. This is the "suggest levers to
grow" behaviour already asked for, with more metrics to read.
"""

# --- write, or check --------------------------------------------------------------
OUTPUTS = {REPO / "data/metric_templates.json": JSON_TEXT,
           REPO / "docs/metric-templates.md": TEXT}
if CHECK_ONLY:
    stale = [p for p, text in OUTPUTS.items()
             if not p.exists() or p.read_text(encoding="utf-8") != text]
    for p in stale:
        print(f"out of date: {p.relative_to(REPO)} — run scripts/build_metric_templates.py")
    sys.exit(1 if stale else 0)
for p, text in OUTPUTS.items():
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
print("written:", ", ".join(str(p.relative_to(REPO)) for p in OUTPUTS))
