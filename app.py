import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# GEOECON v1
# Geothermal Techno-Economic Analyzer
# ============================================================

st.set_page_config(
    page_title="GeoEcon | Geothermal Economic Analyzer",
    page_icon="🌋",
    layout="wide"
)

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def calculate_power(capacity_mw, capacity_factor):
    """
    Annual electrical energy production in kWh.
    """
    hours_per_year = 8760
    annual_energy_kwh = (
        capacity_mw
        * 1000
        * hours_per_year
        * capacity_factor
    )
    return annual_energy_kwh


def calculate_cash_flow(
    capacity_mw,
    capacity_factor,
    electricity_price,
    project_life,
    capex,
    opex,
    discount_rate,
    degradation_rate,
    tax_rate
):
    """
    Creates annual project cash-flow model.
    """

    years = np.arange(0, project_life + 1)

    annual_energy = calculate_power(
        capacity_mw,
        capacity_factor
    )

    revenue = []
    operating_cost = []
    taxable_income = []
    tax = []
    net_cash_flow = []
    discounted_cash_flow = []

    for year in years:

        if year == 0:
            rev = 0
            cost = 0
            taxable = 0
            tax_value = 0
            cash = -capex

        else:
            degradation_factor = (
                (1 - degradation_rate) ** (year - 1)
            )

            energy = annual_energy * degradation_factor

            rev = energy * electricity_price
            cost = opex

            taxable = max(rev - cost, 0)
            tax_value = taxable * tax_rate

            cash = rev - cost - tax_value

        discount_factor = (
            1 / ((1 + discount_rate) ** year)
        )

        discounted = cash * discount_factor

        revenue.append(rev)
        operating_cost.append(cost)
        taxable_income.append(taxable)
        tax.append(tax_value)
        net_cash_flow.append(cash)
        discounted_cash_flow.append(discounted)

    df = pd.DataFrame({
        "Year": years,
        "Revenue": revenue,
        "OPEX": operating_cost,
        "Tax": tax,
        "Net Cash Flow": net_cash_flow,
        "Discounted Cash Flow": discounted_cash_flow
    })

    return df


def calculate_npv(cash_flows, discount_rate):
    """
    NPV calculation.
    """
    return sum(
        cf / ((1 + discount_rate) ** year)
        for year, cf in enumerate(cash_flows)
    )


def calculate_irr(cash_flows):
    """
    IRR using numpy financial-style calculation.
    """
    try:
        return npf_irr(cash_flows)
    except Exception:
        return None


def npf_irr(cash_flows):
    """
    Newton-Raphson IRR calculation.
    """

    rate = 0.1

    for _ in range(100):

        npv = 0
        derivative = 0

        for t, cf in enumerate(cash_flows):

            npv += cf / ((1 + rate) ** t)

            if t > 0:
                derivative += (
                    -t * cf
                    / ((1 + rate) ** (t + 1))
                )

        if abs(derivative) < 1e-12:
            return None

        new_rate = rate - npv / derivative

        if abs(new_rate - rate) < 1e-8:
            return new_rate

        rate = new_rate

    return None


def calculate_payback(cash_flows):
    """
    Simple payback period based on undiscounted cash flow.
    """

    cumulative = 0

    for year, cash_flow in enumerate(cash_flows):

        cumulative += cash_flow

        if cumulative >= 0:

            previous_cumulative = cumulative - cash_flow

            if cash_flow != 0:
                fraction = (
                    -previous_cumulative / cash_flow
                )
            else:
                fraction = 0

            return (year - 1) + fraction

    return None


def calculate_lcoe(
    capacity_mw,
    capacity_factor,
    project_life,
    capex,
    opex,
    discount_rate,
    degradation_rate
):
    """
    Simplified Levelized Cost of Electricity.

    LCOE =
    PV(CAPEX + OPEX)
    ----------------
    PV(Electricity Production)
    """

    annual_energy = calculate_power(
        capacity_mw,
        capacity_factor
    )

    pv_cost = capex
    pv_energy = 0

    for year in range(1, project_life + 1):

        degradation_factor = (
            (1 - degradation_rate) ** (year - 1)
        )

        energy = annual_energy * degradation_factor

        discount_factor = (
            1 / ((1 + discount_rate) ** year)
        )

        pv_cost += opex * discount_factor
        pv_energy += energy * discount_factor

    if pv_energy == 0:
        return None

    return pv_cost / pv_energy


def break_even_price(
    capacity_mw,
    capacity_factor,
    project_life,
    capex,
    opex,
    discount_rate,
    degradation_rate,
    tax_rate
):
    """
    Finds approximate electricity price that makes NPV = 0.
    """

    low = 0.001
    high = 1.00

    for _ in range(100):

        price = (low + high) / 2

        df = calculate_cash_flow(
            capacity_mw,
            capacity_factor,
            price,
            project_life,
            capex,
            opex,
            discount_rate,
            degradation_rate,
            tax_rate
        )

        npv = df["Discounted Cash Flow"].sum()

        if npv > 0:
            high = price
        else:
            low = price

    return (low + high) / 2


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

st.title("🌋 GeoEcon")
st.subheader("Geothermal Techno-Economic Analysis Platform")

st.markdown(
    """
    Evaluate geothermal project economics using engineering,
    financial and sensitivity-analysis parameters.
    """
)

st.divider()

# ------------------------------------------------------------
# Sidebar Inputs
# ------------------------------------------------------------

st.sidebar.header("⚙️ Project Inputs")

technology = st.sidebar.selectbox(
    "Geothermal Technology",
    [
        "Binary Cycle",
        "Flash Steam",
        "Dry Steam",
        "EGS"
    ]
)

st.sidebar.subheader("Engineering")

capacity_mw = st.sidebar.number_input(
    "Plant Capacity (MW)",
    min_value=0.1,
    value=10.0,
    step=0.5
)

capacity_factor = st.sidebar.slider(
    "Capacity Factor",
    min_value=0.10,
    max_value=1.00,
    value=0.90,
    step=0.01
)

st.sidebar.subheader("Economics")

electricity_price = st.sidebar.number_input(
    "Electricity Price ($/kWh)",
    min_value=0.001,
    value=0.08,
    step=0.005
)

capex = st.sidebar.number_input(
    "Initial CAPEX ($)",
    min_value=0.0,
    value=30_000_000.0,
    step=1_000_000.0
)

opex = st.sidebar.number_input(
    "Annual OPEX ($/year)",
    min_value=0.0,
    value=1_000_000.0,
    step=100_000.0
)

project_life = st.sidebar.number_input(
    "Project Life (years)",
    min_value=1,
    max_value=100,
    value=25,
    step=1
)

discount_rate = st.sidebar.number_input(
    "Discount Rate",
    min_value=0.0,
    max_value=1.0,
    value=0.10,
    step=0.01
)

degradation_rate = st.sidebar.number_input(
    "Annual Production Degradation",
    min_value=0.0,
    max_value=0.20,
    value=0.005,
    step=0.001
)

tax_rate = st.sidebar.number_input(
    "Tax Rate",
    min_value=0.0,
    max_value=1.0,
    value=0.25,
    step=0.01
)

# ------------------------------------------------------------
# Calculate
# ------------------------------------------------------------

df = calculate_cash_flow(
    capacity_mw=capacity_mw,
    capacity_factor=capacity_factor,
    electricity_price=electricity_price,
    project_life=int(project_life),
    capex=capex,
    opex=opex,
    discount_rate=discount_rate,
    degradation_rate=degradation_rate,
    tax_rate=tax_rate
)

cash_flows = df["Net Cash Flow"].tolist()

npv = df["Discounted Cash Flow"].sum()

irr = calculate_irr(cash_flows)

payback = calculate_payback(cash_flows)

lcoe = calculate_lcoe(
    capacity_mw,
    capacity_factor,
    int(project_life),
    capex,
    opex,
    discount_rate,
    degradation_rate
)

be_price = break_even_price(
    capacity_mw,
    capacity_factor,
    int(project_life),
    capex,
    opex,
    discount_rate,
    degradation_rate,
    tax_rate
)

annual_energy_mwh = (
    calculate_power(
        capacity_mw,
        capacity_factor
    ) / 1000
)

total_energy_mwh = (
    df["Revenue"].sum() / electricity_price / 1000
)

total_revenue = df["Revenue"].sum()

# ------------------------------------------------------------
# Technology Information
# ------------------------------------------------------------

technology_description = {
    "Binary Cycle":
        "Uses a secondary working fluid and is commonly associated with lower-temperature geothermal resources.",

    "Flash Steam":
        "Uses pressure reduction to convert high-temperature geothermal fluid into steam.",

    "Dry Steam":
        "Uses naturally occurring geothermal steam directly to drive the turbine.",

    "EGS":
        "Enhanced Geothermal Systems aim to create or enhance permeability in hot subsurface rock."
}

st.info(
    f"**Selected Technology: {technology}** — "
    f"{technology_description[technology]}"
)

# ------------------------------------------------------------
# KPI Dashboard
# ------------------------------------------------------------

st.header("📊 Economic Results")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "NPV",
        f"${npv:,.0f}"
    )

with col2:

    if irr is not None:
        st.metric(
            "IRR",
            f"{irr * 100:.2f}%"
        )
    else:
        st.metric("IRR", "N/A")

with col3:

    if payback is not None:
        st.metric(
            "Payback",
            f"{payback:.2f} years"
        )
    else:
        st.metric(
            "Payback",
            "Not reached"
        )

with col4:

    if lcoe is not None:
        st.metric(
            "LCOE",
            f"${lcoe:.4f}/kWh"
        )
    else:
        st.metric(
            "LCOE",
            "N/A"
        )

# ------------------------------------------------------------
# Additional KPIs
# ------------------------------------------------------------

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Annual Generation",
        f"{annual_energy_mwh:,.0f} MWh"
    )

with col2:
    st.metric(
        "Total Revenue",
        f"${total_revenue / 1e6:.2f}M"
    )

with col3:
    st.metric(
        "Break-even Price",
        f"${be_price:.4f}/kWh"
    )

with col4:
    st.metric(
        "Project Capacity",
        f"{capacity_mw:.1f} MW"
    )

# ------------------------------------------------------------
# Cash Flow Chart
# ------------------------------------------------------------

st.header("💰 Cash Flow Analysis")

fig_cash = go.Figure()

fig_cash.add_trace(
    go.Bar(
        x=df["Year"],
        y=df["Net Cash Flow"],
        name="Net Cash Flow"
    )
)

fig_cash.add_trace(
    go.Scatter(
        x=df["Year"],
        y=df["Discounted Cash Flow"],
        mode="lines+markers",
        name="Discounted Cash Flow"
    )
)

fig_cash.update_layout(
    title="Annual Cash Flow",
    xaxis_title="Year",
    yaxis_title="Cash Flow ($)",
    hovermode="x unified"
)

st.plotly_chart(
    fig_cash,
    use_container_width=True
)

# ------------------------------------------------------------
# Cumulative Cash Flow
# ------------------------------------------------------------

df["Cumulative Cash Flow"] = (
    df["Net Cash Flow"].cumsum()
)

fig_cumulative = go.Figure()

fig_cumulative.add_trace(
    go.Scatter(
        x=df["Year"],
        y=df["Cumulative Cash Flow"],
        mode="lines+markers",
        name="Cumulative Cash Flow"
    )
)

fig_cumulative.add_hline(
    y=0,
    line_dash="dash"
)

fig_cumulative.update_layout(
    title="Cumulative Cash Flow",
    xaxis_title="Year",
    yaxis_title="Cumulative Cash Flow ($)"
)

st.plotly_chart(
    fig_cumulative,
    use_container_width=True
)

# ------------------------------------------------------------
# Sensitivity Analysis
# ------------------------------------------------------------

st.header("📈 Sensitivity Analysis")

st.write(
    "The following analysis shows how NPV changes when "
    "major economic parameters are varied."
)

sensitivity_parameter = st.selectbox(
    "Select Parameter",
    [
        "CAPEX",
        "Electricity Price",
        "OPEX",
        "Discount Rate",
        "Capacity Factor"
    ]
)

multipliers = np.arange(
    0.70,
    1.31,
    0.05
)

sensitivity_results = []

for multiplier in multipliers:

    test_capex = capex
    test_price = electricity_price
    test_opex = opex
    test_discount = discount_rate
    test_capacity_factor = capacity_factor

    if sensitivity_parameter == "CAPEX":
        test_capex = capex * multiplier

    elif sensitivity_parameter == "Electricity Price":
        test_price = electricity_price * multiplier

    elif sensitivity_parameter == "OPEX":
        test_opex = opex * multiplier

    elif sensitivity_parameter == "Discount Rate":
        test_discount = discount_rate * multiplier

    elif sensitivity_parameter == "Capacity Factor":
        test_capacity_factor = min(
            capacity_factor * multiplier,
            1.0
        )

    test_df = calculate_cash_flow(
        capacity_mw,
        test_capacity_factor,
        test_price,
        int(project_life),
        test_capex,
        test_opex,
        test_discount,
        degradation_rate,
        tax_rate
    )

    test_npv = test_df[
        "Discounted Cash Flow"
    ].sum()

    sensitivity_results.append(test_npv)

sensitivity_df = pd.DataFrame({
    "Multiplier": multipliers,
    "NPV": sensitivity_results
})

fig_sensitivity = go.Figure()

fig_sensitivity.add_trace(
    go.Scatter(
        x=sensitivity_df["Multiplier"] * 100,
        y=sensitivity_df["NPV"],
        mode="lines+markers"
    )
)

fig_sensitivity.add_hline(
    y=0,
    line_dash="dash"
)

fig_sensitivity.update_layout(
    title=f"NPV Sensitivity to {sensitivity_parameter}",
    xaxis_title=f"{sensitivity_parameter} (% of Base Case)",
    yaxis_title="NPV ($)"
)

st.plotly_chart(
    fig_sensitivity,
    use_container_width=True
)

# ------------------------------------------------------------
# Cash Flow Table
# ------------------------------------------------------------

with st.expander("📋 View Detailed Cash Flow"):

    formatted_df = df.copy()

    for column in [
        "Revenue",
        "OPEX",
        "Tax",
        "Net Cash Flow",
        "Discounted Cash Flow",
        "Cumulative Cash Flow"
    ]:
        formatted_df[column] = formatted_df[column].round(2)

    st.dataframe(
        formatted_df,
        use_container_width=True
    )

# ------------------------------------------------------------
# Project Summary
# ------------------------------------------------------------

st.header("📝 Project Summary")

if npv > 0:
    npv_statement = (
        "The calculated NPV is positive under the entered assumptions."
    )
elif npv < 0:
    npv_statement = (
        "The calculated NPV is negative under the entered assumptions."
    )
else:
    npv_statement = (
        "The calculated NPV is approximately zero under the entered assumptions."
    )

st.write(
    f"""
    **Technology:** {technology}

    **Capacity:** {capacity_mw:.2f} MW

    **Project Life:** {project_life:.0f} years

    **{npv_statement}**

    **Break-even electricity price:** ${be_price:.4f}/kWh

    These results are model outputs based on the assumptions entered by
    the user. They should not be interpreted as a feasibility conclusion
    without validating the engineering, financial, geological and market
    assumptions.
    """
)

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------

st.divider()

st.caption(
    "GeoEcon v1.0 | Python + Streamlit | "
    "Geothermal Techno-Economic Analysis"
)
