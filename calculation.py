import streamlit as st
import math
import pandas as pd
import datetime # For time formatting
# Removed PDF/OS/ReportLab imports

# --- Constants ---
PITCH = 3.175; GAP_MIN = 2.5; GAP_MAX = 4.0; Z_MIN = 70; Z_MAX = 140
TOTAL_CYLINDER_WIDTH = 200; WORKING_WIDTH = 190; WIDTH_GAP = 5
WIDTH_WASTE = 10; MAX_MATERIAL_WIDTH = 200
BASE_WASTE_LENGTH = 50.0; WASTE_LENGTH_PER_COLOR = 50.0
SETUP_TIME_PER_COLOR_OR_BASE = 30; CLEANUP_TIME_MIN = 30
MACHINE_SPEED_DEFAULT = 30; MACHINE_SPEED_MIN = 10; MACHINE_SPEED_MAX = 120
GRAMS_INK_PER_M2 = 3.0; GRAMS_VARNISH_PER_M2 = 4.0
INK_PRICE_PER_KG_DEFAULT = 2350.0; VARNISH_PRICE_PER_KG_DEFAULT = 1800.0
MACHINE_LABOR_PRICE_PER_HOUR_DEFAULT = 3000.0
TOOL_PRICE_SEMIROTARY_DEFAULT = 6000.0
TOOL_PRICE_ROTARY_DEFAULT = 8000.0
PROFIT_COEFFICIENT_DEFAULT = 0.20
PLATE_PRICE_PER_COLOR_DEFAULT = 2000.0

# Default materials and prices (RSD/m²)
DEFAULT_MATERIALS_PRICES = {
    "Paper (chrome)": 39.95,
    "Plastic (PPW)": 54.05,
    "Thermal Paper": 49.35
}

# --- Session State Initialization ---
# Removed 'language' state
if 'materials_prices' not in st.session_state: st.session_state.materials_prices = DEFAULT_MATERIALS_PRICES.copy()
if 'ink_price_per_kg' not in st.session_state: st.session_state.ink_price_per_kg = INK_PRICE_PER_KG_DEFAULT
if 'varnish_price_per_kg' not in st.session_state: st.session_state.varnish_price_per_kg = VARNISH_PRICE_PER_KG_DEFAULT
if 'machine_labor_price_per_hour' not in st.session_state: st.session_state.machine_labor_price_per_hour = MACHINE_LABOR_PRICE_PER_HOUR_DEFAULT
if 'tool_price_semirotary' not in st.session_state: st.session_state.tool_price_semirotary = TOOL_PRICE_SEMIROTARY_DEFAULT
if 'tool_price_rotary' not in st.session_state: st.session_state.tool_price_rotary = TOOL_PRICE_ROTARY_DEFAULT
if 'existing_tool_info' not in st.session_state: st.session_state.existing_tool_info = ""
if 'plate_price_per_color' not in st.session_state: st.session_state.plate_price_per_color = PLATE_PRICE_PER_COLOR_DEFAULT

# --- Calculation Functions ---
def find_cylinder_specifications(template_width_W):
    valid_solutions = []; message = ""
    if template_width_W <= 0: return None, [], "Error: Template width must be > 0."
    for z in range(Z_MIN, Z_MAX + 1):
        circumference_C = z * PITCH
        if (template_width_W + GAP_MIN) <= 1e-9: continue
        n_max_possible = math.floor(circumference_C / (template_width_W + GAP_MIN))
        for n in range(1, n_max_possible + 1):
            if n == 0: continue
            gap_G_circumference = (circumference_C / n) - template_width_W
            tolerance = 1e-9
            if (GAP_MIN - tolerance) <= gap_G_circumference <= (GAP_MAX + tolerance):
                valid_solutions.append({"number_of_teeth_Z": z, "circumference_mm": circumference_C, "templates_N_circumference": n, "gap_G_circumference_mm": gap_G_circumference})
    if not valid_solutions:
        message = f"No cylinder found ({Z_MIN}-{Z_MAX} teeth) for W={template_width_W:.3f}mm with G={GAP_MIN:.1f}-{GAP_MAX:.1f}mm."
        return None, [], message
    valid_solutions.sort(key=lambda x: (x["number_of_teeth_Z"], -x["templates_N_circumference"]))
    return valid_solutions[0], valid_solutions, "Circumference calculation OK."

def calculate_number_across_width(template_height_H, working_width, width_gap):
    if template_height_H <= 0: return 0
    if template_height_H > working_width: return 0
    if template_height_H <= working_width and (template_height_H * 2 + width_gap) > working_width: return 1
    denominator = template_height_H + width_gap
    if denominator <= 1e-9: return 0
    return int(math.floor((working_width + width_gap) / denominator))

def calculate_material_width(number_across_width_y, template_height_H, width_gap, width_waste):
    if number_across_width_y <= 0: return 0
    total_template_width = number_across_width_y * template_height_H
    total_gap_width = max(0, number_across_width_y - 1) * width_gap
    return total_template_width + total_gap_width + width_waste

def format_time(total_minutes):
    if total_minutes < 0: return "N/A"
    total_minutes = round(total_minutes)
    if total_minutes == 0: return "0 min"
    if total_minutes < 60: return f"{total_minutes} min"
    hours, minutes = divmod(total_minutes, 60)
    if minutes == 0: return f"{hours} h"
    return f"{hours} h {minutes} min"

# --- Streamlit Application ---
st.set_page_config(page_title="Print Calculation", layout="wide")
st.title("📊 Label Printing Cost Calculator")

col_info1, col_info2 = st.columns(2)
with col_info1: client_name = st.text_input("Client Name:")
with col_info2: product_name = st.text_input("Product/Label Name:")
st.markdown("---")
st.markdown("Enter the print parameters and adjust prices/coefficients in the **left sidebar**. The application calculates all necessary values for the estimation.")

# --- Sidebar ---
st.sidebar.header("Input Parameters")
template_width_W_input = st.sidebar.number_input("Template Width (along circumference, mm):", 0.1, value=76.0, step=0.1, format="%.3f")
template_height_H_input = st.sidebar.number_input("Template Height (across cylinder width, mm):", 0.1, value=76.0, step=0.1, format="%.3f")
quantity_input = st.sidebar.number_input("Desired Quantity (pieces):", 1, value=100000, step=1000, format="%d")

st.sidebar.markdown("---"); st.sidebar.subheader("Ink, Varnish, and Plate Settings")
is_blank = st.sidebar.checkbox("Blank Template (no ink)", value=False, help="No cost for ink and plates.")
num_colors_input = st.sidebar.number_input("Number of Colors:", 1, 8, value=1, step=1, format="%d", disabled=is_blank)
is_uv_varnish_input = st.sidebar.checkbox("UV Varnish", value=False, help=f"Adds UV varnish cost ({GRAMS_VARNISH_PER_M2}g/m²).")
current_ink_price = st.session_state.ink_price_per_kg; ink_price_kg_input = st.sidebar.number_input("Ink Price (RSD/kg):", 0.0, value=current_ink_price, step=10.0, format="%.2f", help=f"Def: {INK_PRICE_PER_KG_DEFAULT:.2f}")
if ink_price_kg_input != current_ink_price: st.session_state.ink_price_per_kg = ink_price_kg_input
current_varnish_price = st.session_state.varnish_price_per_kg; varnish_price_kg_input = st.sidebar.number_input("UV Varnish Price (RSD/kg):", 0.0, value=current_varnish_price, step=10.0, format="%.2f", help=f"Def: {VARNISH_PRICE_PER_KG_DEFAULT:.2f}")
if varnish_price_kg_input != current_varnish_price: st.session_state.varnish_price_per_kg = varnish_price_kg_input
current_plate_price = st.session_state.plate_price_per_color; plate_price_input = st.sidebar.number_input("Plate Price per Color (RSD):", 0.0, value=current_plate_price, step=50.0, format="%.2f", help=f"One-time cost per print color. Def: {PLATE_PRICE_PER_COLOR_DEFAULT:.2f}")
if plate_price_input != current_plate_price: st.session_state.plate_price_per_color = plate_price_input

st.sidebar.markdown("---"); st.sidebar.subheader("Machine")
machine_speed_m_min = st.sidebar.slider("Average Machine Speed (m/min):", MACHINE_SPEED_MIN, MACHINE_SPEED_MAX, MACHINE_SPEED_DEFAULT, 5)
current_labor_price = st.session_state.machine_labor_price_per_hour; labor_price_h_input = st.sidebar.number_input("Machine Labor Price (RSD/h):", 0.0, value=current_labor_price, step=50.0, format="%.2f", help=f"Def: {MACHINE_LABOR_PRICE_PER_HOUR_DEFAULT:.2f}")
if labor_price_h_input != current_labor_price: st.session_state.machine_labor_price_per_hour = labor_price_h_input

st.sidebar.markdown("---"); st.sidebar.subheader("Cutting Tool")
tool_type_options_keys = ["None", "Semirotary", "Rotary"]; selected_tool_key = st.sidebar.radio("Select tool type:", options=tool_type_options_keys, index=0, key="tool_type_radio")
existing_tool_info = ""
if selected_tool_key == "None":
    st.session_state.existing_tool_info = st.sidebar.text_input("Existing tool ID/Name:", value=st.session_state.existing_tool_info, help="Enter the identifier of the tool you already have.")
    existing_tool_info = st.session_state.existing_tool_info
current_price_semirotary = st.session_state.tool_price_semirotary; tool_price_semi_input = st.sidebar.number_input("Semirotary Tool Price (RSD):", 0.0, value=current_price_semirotary, step=100.0, format="%.2f", help=f"Def: {TOOL_PRICE_SEMIROTARY_DEFAULT:.2f}")
if tool_price_semi_input != current_price_semirotary: st.session_state.tool_price_semirotary = tool_price_semi_input
current_price_rotary = st.session_state.tool_price_rotary; tool_price_rot_input = st.sidebar.number_input("Rotary Tool Price (RSD):", 0.0, value=current_price_rotary, step=100.0, format="%.2f", help=f"Def: {TOOL_PRICE_ROTARY_DEFAULT:.2f}")
if tool_price_rot_input != current_price_rotary: st.session_state.tool_price_rotary = tool_price_rot_input

st.sidebar.markdown("---"); st.sidebar.subheader("Material")
material_list = list(st.session_state.materials_prices.keys()); selected_material = st.sidebar.selectbox("Select material type:", options=material_list, index=0)
current_material_price = st.session_state.materials_prices.get(selected_material, 0.0); material_price_label_formatted = f"Price for '{selected_material}' (RSD/m²):"
price_per_m2_input = st.sidebar.number_input(material_price_label_formatted, 0.0, value=current_material_price, step=0.1, format="%.2f")
if price_per_m2_input != current_material_price: st.session_state.materials_prices[selected_material] = price_per_m2_input

st.sidebar.markdown("---"); st.sidebar.subheader("Profit Coefficient")
profit_coefficient_input = st.sidebar.slider("Profit coefficient (on material cost):", 0.01, 2.00, PROFIT_COEFFICIENT_DEFAULT, 0.01, format="%.2f", help=f"Def: {PROFIT_COEFFICIENT_DEFAULT:.2f}")

# --- Calculation and Results Display ---
inputs_valid = template_width_W_input and template_height_H_input and quantity_input > 0 and machine_speed_m_min and selected_material and price_per_m2_input is not None and labor_price_h_input is not None and selected_tool_key is not None and profit_coefficient_input is not None

if inputs_valid:

    # 1. Circumference; 2. Width ('y')
    best_circumference_solution, all_circumference_solutions, circumference_message = find_cylinder_specifications(template_width_W_input)
    number_across_width_y = calculate_number_across_width(template_height_H_input, WORKING_WIDTH, WIDTH_GAP)

    if best_circumference_solution:
        st.header("📊 Calculation Results")

        # Values from solution
        number_circumference_x = best_circumference_solution['templates_N_circumference']; gap_G_circumference_mm = best_circumference_solution['gap_G_circumference_mm']
        total_templates_per_cycle = number_across_width_y * number_circumference_x
        valid_num_colors_for_calc = 0 if is_blank else (num_colors_input if num_colors_input is not None and num_colors_input >= 1 else 1)

        # 3. Material Width
        required_material_width_mm = calculate_material_width(number_across_width_y, template_height_H_input, WIDTH_GAP, WIDTH_WASTE)
        material_width_exceeded = required_material_width_mm > MAX_MATERIAL_WIDTH

        # 4. Material Consumption for PRODUCTION
        total_production_length_m = 0.0; total_production_area_m2 = 0.0; production_consumption_message = ""
        if number_across_width_y > 0: segment_length_mm = template_width_W_input + gap_G_circumference_mm; total_production_length_m = (quantity_input / number_across_width_y) * segment_length_mm / 1000
        if required_material_width_mm > 0 and number_across_width_y > 0: total_production_area_m2 = total_production_length_m * (required_material_width_mm / 1000)
        elif number_across_width_y > 0 : production_consumption_message = "Width=0, area N/A."
        else: production_consumption_message = "y=0, consumption N/A."

        # 5. Material Consumption for WASTE
        waste_length_m = 0.0; waste_area_m2 = 0.0; waste_description = ""; num_colors_for_waste_time = 1 if is_blank else valid_num_colors_for_calc
        if is_blank: waste_length_m = BASE_WASTE_LENGTH; waste_description = f"Blank ({BASE_WASTE_LENGTH}m)"
        else: waste_length_m = BASE_WASTE_LENGTH + (valid_num_colors_for_calc * WASTE_LENGTH_PER_COLOR); waste_description = f"{valid_num_colors_for_calc} color{'s' if valid_num_colors_for_calc!=1 else ''} ({BASE_WASTE_LENGTH}+{valid_num_colors_for_calc}×{WASTE_LENGTH_PER_COLOR}m)"
        if required_material_width_mm > 0: waste_area_m2 = waste_length_m * (required_material_width_mm / 1000)

        # 6. TOTAL Material Consumption
        total_final_length_m = total_production_length_m + waste_length_m
        total_final_area_m2 = total_production_area_m2 + waste_area_m2

        # 7. Time Calculation
        setup_time_min = num_colors_for_waste_time * SETUP_TIME_PER_COLOR_OR_BASE
        production_time_min = (total_production_length_m / machine_speed_m_min) if total_production_length_m > 0 and machine_speed_m_min > 0 else 0.0
        cleanup_time_min = CLEANUP_TIME_MIN; total_time_min = setup_time_min + production_time_min + cleanup_time_min

        # --- Cost Calculations ---
        # 8. Ink and Varnish Cost
        ink_cost_rsd = 0.0; ink_consumption_kg = 0.0; varnish_cost_rsd = 0.0; varnish_consumption_kg = 0.0
        if not is_blank and valid_num_colors_for_calc > 0 and total_production_area_m2 > 0: ink_consumption_g = total_production_area_m2 * valid_num_colors_for_calc * GRAMS_INK_PER_M2; ink_consumption_kg = ink_consumption_g / 1000.0; ink_cost_rsd = ink_consumption_kg * st.session_state.ink_price_per_kg
        if is_uv_varnish_input and total_production_area_m2 > 0: varnish_consumption_g = total_production_area_m2 * GRAMS_VARNISH_PER_M2; varnish_consumption_kg = varnish_consumption_g / 1000.0; varnish_cost_rsd = varnish_consumption_kg * st.session_state.varnish_price_per_kg
        total_ink_varnish_cost_rsd = ink_cost_rsd + varnish_cost_rsd

        # 9. Plate Cost
        total_plate_cost_rsd = 0.0
        if not is_blank and valid_num_colors_for_calc > 0: total_plate_cost_rsd = valid_num_colors_for_calc * st.session_state.plate_price_per_color

        # 10. Material Cost
        total_material_cost_rsd = 0.0
        if total_final_area_m2 > 0 and price_per_m2_input >= 0: total_material_cost_rsd = total_final_area_m2 * price_per_m2_input

        # 11. Machine Labor Cost
        total_machine_labor_cost_rsd = 0.0
        if total_time_min > 0 and st.session_state.machine_labor_price_per_hour >= 0: total_time_h = total_time_min / 60.0; total_machine_labor_cost_rsd = total_time_h * st.session_state.machine_labor_price_per_hour

        # 12. Tool Cost
        total_tool_cost_rsd = 0.0; tool_description_display = "Not selected"
        if selected_tool_key == "Semirotary": total_tool_cost_rsd = st.session_state.tool_price_semirotary; tool_description_display = f"Semirotary ({st.session_state.tool_price_semirotary:,.2f} RSD)"
        elif selected_tool_key == "Rotary": total_tool_cost_rsd = st.session_state.tool_price_rotary; tool_description_display = f"Rotary ({st.session_state.tool_price_rotary:,.2f} RSD)"
        elif selected_tool_key == "None": tool_description_display = f"Existing: {existing_tool_info}" if existing_tool_info else "Not selected"
        tool_info_string = f"Existing: {existing_tool_info}" if selected_tool_key == "None" and existing_tool_info else selected_tool_key

        # 13. Total Production Cost
        total_production_cost_rsd = (total_ink_varnish_cost_rsd + total_plate_cost_rsd + total_material_cost_rsd + total_machine_labor_cost_rsd + total_tool_cost_rsd)

        # 14. Profit Calculation
        profit_rsd = 0.0
        if total_material_cost_rsd > 0 and profit_coefficient_input > 0: profit_rsd = total_material_cost_rsd * profit_coefficient_input

        # 15. Final Selling Price
        total_selling_price_rsd = total_production_cost_rsd + profit_rsd
        selling_price_per_piece_rsd = (total_selling_price_rsd / quantity_input) if quantity_input > 0 else 0.0

        # --- Results Display ---
        st.subheader(f"Calculation for: {product_name if product_name else '[Product]'} | Client: {client_name if client_name else '[Client]'}")
        st.markdown("---")

        with st.expander("Calculation Details (Configuration, Consumption, Time)"):
            params_dims = f"W:{template_width_W_input:.2f}×H:{template_height_H_input:.2f}mm"; params_qty = f"Qty:{quantity_input:,}"
            params_colors = 'Blank' if is_blank else str(valid_num_colors_for_calc)+'C'; params_varnish = '+V' if is_uv_varnish_input else ''
            params_mat = f"Mat:'{selected_material}'"; params_tool = f"Tool:'{tool_info_string}'"; params_speed = f"Speed:{machine_speed_m_min}m/min"; params_profit = f"Prof.Coef:{profit_coefficient_input:.2f}"
            st.write(f"**Parameters:** {params_dims} | {params_qty} | {params_colors}{params_varnish} | {params_mat} | {params_tool} | {params_speed} | {params_profit}")
            st.markdown("---")

            st.subheader("1. Cylinder and Template Configuration"); col1, col2 = st.columns(2);
            with col1: st.metric("Number of Teeth (Z)", f"{best_circumference_solution['number_of_teeth_Z']}"); st.metric("Cylinder Circumference", f"{best_circumference_solution['circumference_mm']:.3f} mm"); st.metric("Circumference Gap (G)", f"{gap_G_circumference_mm:.3f} mm", help=f"{GAP_MIN:.1f}-{GAP_MAX:.1f} mm")
            with col2: st.metric("Templates Circumference (x)", f"{number_circumference_x}"); st.metric("Templates Width (y)", f"{number_across_width_y}", help=f"On {WORKING_WIDTH}mm"); st.metric("Format (y × x)", f"{number_across_width_y} × {number_circumference_x}", help="/cycle")

            st.subheader("2. Material Width Calculation");
            if number_across_width_y > 0:
                mat_col1, mat_col2 = st.columns([2,1]); help_width = f"({number_across_width_y}×{template_height_H_input:.2f}mm)+({max(0, number_across_width_y-1)}×{WIDTH_GAP}mm)+{WIDTH_WASTE}mm";
                with mat_col1: st.metric("Required Material Width", f"{required_material_width_mm:.2f} mm", help=help_width)
                with mat_col2:
                    if not material_width_exceeded: st.success(f"✅ OK (≤ {MAX_MATERIAL_WIDTH} mm)")
                    else: st.error(f"⚠️ EXCEEDED! >{MAX_MATERIAL_WIDTH} mm")
            else: st.warning("y=0, material width N/A.")

            st.subheader(f"3. Material Consumption for PRODUCTION ({quantity_input:,} pcs)");
            if number_across_width_y > 0:
                pro_col1, pro_col2 = st.columns(2);
                with pro_col1: st.metric("Length (Production)", f"{total_production_length_m:,.2f} m")
                with pro_col2: st.metric("Area (Production)", f"{total_production_area_m2:,.2f} m²")
                if production_consumption_message and "N/A" not in production_consumption_message: st.warning(production_consumption_message)
            else: st.warning(production_consumption_message)

            st.subheader(f"4. Material Consumption for WASTE (Setup)");
            ska_col1, ska_col2 = st.columns(2);
            with ska_col1: st.metric("Length (Waste)", f"{waste_length_m:,.2f} m", help=waste_description)
            with ska_col2:
                if required_material_width_mm > 0: help_waste_area = f"= {waste_length_m:,.2f}m*({required_material_width_mm:.2f}mm/1000)"; st.metric("Area (Waste)", f"{waste_area_m2:,.2f} m²", help=help_waste_area)
                else: st.info("Waste Area N/A (width=0)")

            st.subheader(f"5. TOTAL Estimated Material Consumption");
            tot_col1, tot_col2 = st.columns(2);
            with tot_col1: st.metric("TOTAL Length", f"{total_final_length_m:,.2f} m", help="Production + Waste")
            with tot_col2: st.metric("TOTAL Area", f"{total_final_area_m2:,.2f} m²", help="Production + Waste")

            st.subheader("6. Estimated Production Time"); time_col1, time_col2, time_col3, time_col4 = st.columns(4);
            with time_col1: st.metric("Setup Time", format_time(setup_time_min), help=f"{num_colors_for_waste_time} × {SETUP_TIME_PER_COLOR_OR_BASE}min")
            with time_col2: st.metric("Production Time", format_time(production_time_min), help=f"{total_production_length_m:,.1f}m / {machine_speed_m_min}m/min")
            with time_col3: st.metric("Cleanup Time", format_time(cleanup_time_min), help="Fixed")
            with time_col4: st.metric("TOTAL Work Time", format_time(total_time_min), help="Σ Setup+Production+Cleanup")

            if len(all_circumference_solutions) > 1:
                st.subheader("Other Possible Solutions for Cylinder Circumference")
                st.caption("(Sorted by Z ↑, then by x ↓)")
                other_solutions_data = [sol for sol in all_circumference_solutions if sol != best_circumference_solution];
                if other_solutions_data:
                    df_others = pd.DataFrame(other_solutions_data);
                    df_others = df_others.rename(columns={
                        "number_of_teeth_Z": "Z",
                        "circumference_mm": "Circumference",
                        "templates_N_circumference": "x",
                        "gap_G_circumference_mm": "G Circum."
                    })
                    df_others['Circumference'] = df_others['Circumference'].map('{:.3f}'.format);
                    df_others['G Circum.'] = df_others['G Circum.'].map('{:.3f}'.format);
                    st.dataframe(df_others, use_container_width=True)

        st.markdown("---")

        st.subheader("📊 Cost Calculation")
        cost_row1_cols = st.columns(5) # Now 5 columns
        with cost_row1_cols[0]: st.metric("Cost: Ink + Varnish", f"{total_ink_varnish_cost_rsd:,.2f} RSD", help=f"Ink:{ink_cost_rsd:,.2f}, Varnish:{varnish_cost_rsd:,.2f}")
        with cost_row1_cols[1]: st.metric("Cost: Plates", f"{total_plate_cost_rsd:,.2f} RSD", help=f"{valid_num_colors_for_calc}×{st.session_state.plate_price_per_color:.2f} RSD/color")
        with cost_row1_cols[2]: st.metric("Cost: Material", f"{total_material_cost_rsd:,.2f} RSD", help=f"{total_final_area_m2:,.2f}m²×{price_per_m2_input:.2f}RSD/m²")
        with cost_row1_cols[3]: st.metric("Cost: Tool", f"{total_tool_cost_rsd:,.2f} RSD", help=tool_description_display)
        with cost_row1_cols[4]: # Machine labor in 5th column
             total_time_h_for_help = total_time_min / 60.0
             st.metric("Cost: Machine Labor", f"{total_machine_labor_cost_rsd:,.2f} RSD", help=f"{format_time(total_time_min)}({total_time_h_for_help:.2f}h)×{st.session_state.machine_labor_price_per_hour:.2f}RSD/h")

        st.subheader("💰 Profit and Final Selling Price")
        final_col1, final_col2, final_col3 = st.columns(3)
        with final_col1: st.metric("Total Production Cost", f"{total_production_cost_rsd:,.2f} RSD", help="Σ (Ink/Varnish + Plates + Material + Labor + Tool)")
        with final_col2: st.metric("Profit", f"{profit_rsd:,.2f} RSD", help=f"({profit_coefficient_input:.2f} × Material Cost)", delta=f"{profit_coefficient_input*100:.0f}%")
        with final_col3: st.metric("TOTAL PRICE (Selling)", f"{total_selling_price_rsd:,.2f} RSD", delta=f"{profit_rsd:,.2f} RSD", help="Production Cost + Profit")

        st.metric("Selling Price per Piece", f"{selling_price_per_piece_rsd:.4f} RSD", help=f"= {total_selling_price_rsd:,.2f} RSD / {quantity_input:,} pcs")

    else: # If no circumference solution was found
        error_msg = f"No cylinder found ({Z_MIN}-{Z_MAX} teeth) for W={template_width_W_input:.3f}mm with G={GAP_MIN:.1f}-{GAP_MAX:.1f}mm." if circumference_message and 'No cylinder found' in circumference_message else f"Calculation error: {circumference_message}"
        if "Error" in circumference_message: st.error(f"❌ {error_msg}")
        else: st.warning(f"⚠️ {error_msg}")

else: # If not all required inputs are entered
    st.info("Enter all parameters in the left panel (minimum Width, Height, and Quantity > 0).")

st.markdown("---")
settings_str = f"MaxMat={MAX_MATERIAL_WIDTH}mm | LaborPrice={st.session_state.machine_labor_price_per_hour:.2f}RSD/h | Tools: Semi={st.session_state.tool_price_semirotary:.2f}, Rot={st.session_state.tool_price_rotary:.2f} | Plate={st.session_state.plate_price_per_color:.2f}RSD/color"
st.caption(settings_str)