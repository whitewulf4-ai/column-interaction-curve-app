import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import os
from PIL import Image
from io import BytesIO
import pandas as pd
import io
import xlsxwriter

# Title
st.title("ACI 318-19 Interaction Diagram for Concrete Column")

with st.expander("ℹ️ Click here for Instructions and Explanations"):
    st.markdown("""
    **Instructions:**
    - Input the column dimensions, reinforcement details and material properties in the sidebar.
    - Upload Excel files (if available) with design points, to plot points on the interaction diagram. Excel files should contain two columns: 'Pu' and 'Mu'.
    - View interaction diagrams for bending about strong and weak axes.
    - Download the plotted diagrams using the buttons below each plot.
    - Download Excel file with points for interaction curve. """)
    st.markdown("""
    **Notes:**
    - Reinforcement inputs should be comma-separated values.
    - Reinforcement positions should be measured from the top for vertical bars and from the left for horizontal bars.
    - All dimensions are in **mm**, and forces in **kN**.
    - The program draws two interaction diagrams:
        - **Red** for bending about the strong axis
        - **Blue** for bending about the weak axis
        
                 Note: The diagrams about strong axis (red) are based only on the major reinforcement (As_red) and the diagrams about weak axis (blue) are based only on the 
                    minor reinforcement (As_blue). In other words, directions are considered separately

    - In case of need, the biaxial moment strength can be calculated using Equation 5.12.8 given in ACI 314R-16:
    """)
    
    st.latex(r"\frac{M_{ux}}{\phi M_{nx}} + \frac{M_{uy}}{\phi M_{ny}} \leq 1.0")
    
    st.markdown("""
                    $M_{ux}$, $M_{uy}$: factored design moments about the x- and y-axes.<br>
                    $\phi M_{nx}$, $\phi M_{ny}$: nominal moment capacities about the x- and y-axes (from interaction diagram, value where $P_n=0$).
    """, unsafe_allow_html=True)
    
    st.markdown("""
    - Diagrams are based on ACI 318-19 provisions.
    """)


st.markdown("### Designed for rectangular cross-sections with symmetric reinforcement")

# Inject CSS to widen the main area
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1600px;
        margin: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.sidebar.header("Input Parameters") 

# Inputs
b = st.sidebar.number_input("Width b (mm)", value=500)
h = st.sidebar.number_input("Height h (mm)", value=600)

with st.sidebar:
    # Raw input as a comma-separated string
    As_v_str = st.text_input("Major reinforcement (As_red) [mm²]", "4021, 2412, 2412, 4021")
    dis_top_str = st.text_input("Reinforcement positions from top (dis_top) [mm]", "50, 150, 450, 550")

    # Convert to list of numbers
    try:
        As_v = [float(x.strip()) for x in As_v_str.split(',')]
        dis_top = [float(x.strip()) for x in dis_top_str.split(',')]
    except ValueError:
        st.error("Invalid input. Please enter numbers separated by commas.")
        st.stop()

    # Raw input as a comma-separated string
    As_h_str = st.text_input("Minor reinforcement (As_blue) [mm²]", "2412, 2412")
    dis_left_str = st.text_input("Reinforcement positions from left (dis_left) [mm]", "50, 450")

    # Convert to list of numbers
    try:
        As_h = [float(x.strip()) for x in As_h_str.split(',')]
        dis_left = [float(x.strip()) for x in dis_left_str.split(',')]
    except ValueError:
        st.error("Invalid input. Please enter numbers separated by commas.")
        st.stop()

fc = st.sidebar.number_input("Concrete Strength fc (MPa)", value=30)
fy = st.sidebar.number_input("Steel Yield Strength fy (MPa)", value=410)
Es = st.sidebar.number_input("Modulus of Elasticity Es (MPa)", value=200000)

transferse_reinforcement_type = st.sidebar.selectbox("Transverse Reinforcement Type", ["Ties", "Spiral"])


def draw_section(As_v, dis_top, As_h, dis_left):
    fig, ax = plt.subplots()

    rect = plt.Rectangle((0, 0), b, h, fill=None, edgecolor='black', linewidth=2)
    ax.add_patch(rect)

    rect_height = 20
    rect_width_h = 20

    for area, y in zip(As_v, dis_top):
        rect_width = area / rect_height
        x = (b - rect_width) / 2
        bar_rect = plt.Rectangle((x, y - rect_height / 2), rect_width, rect_height,
                                color='red', alpha=0.6)
        ax.add_patch(bar_rect)
        ax.text(x + rect_width / 2, y, f"{int(area)} mm²",
                ha='center', va='center', color='black', fontsize=9, fontweight='bold')

    for area, x in zip(As_h, dis_left):
        rect_height_h = area / rect_width_h
        left_bar = plt.Rectangle((x - rect_width_h / 2, (h - rect_height_h) / 2),
                                rect_width_h, rect_height_h, color='blue', alpha=0.6)
        ax.add_patch(left_bar)
        ax.text(x, h / 2, f"{int(area)} mm²", ha='center', va='center',
                color='black', fontsize=9, fontweight='bold', rotation=90)

    ax.set_xlim(-50, b + 50)
    ax.set_ylim(-50, h + 50)
    ax.set_aspect('equal')
    ax.set_title("Column Section with Vertical & Horizontal Bar Areas")
    ax.set_xlabel("Width (mm)")
    ax.set_ylabel("Height (mm)")
    ax.grid(True)

    return fig

fig_section = draw_section(As_v, dis_top, As_h, dis_left)
st.sidebar.pyplot(fig_section)


########################################
# Total area of bars
As_tot = sum(As_v)

# Gross area of the column
Ag = b * h


# Function to reverce lists 
def reverse_list(As_h, dis_left, As_v, dis_top):
    As_h = As_h[::-1]
    dis_left = dis_left[::-1]

    As_v = As_v[::-1]
    dis_top = dis_top[::-1]
    
    return As_h, dis_left, As_v, dis_top

As_h, dis_left, As_v, dis_top = reverse_list(As_h, dis_left, As_v, dis_top)

# Transferse reinforcement type ------ ACI 318-19 Table22.4.2.1
if transferse_reinforcement_type == 'Spiral':
    alpha = 0.85
else:
    alpha = 0.8  

print(f"Transferse reinforcement type = {transferse_reinforcement_type}")
print(f"α = {alpha} (ACI 318-19 Table 22.4.2.1)")

# Maximum axial compressive strength - ACI 318-19 Chapter 22.4.2
Po = (0.85 * fc * (Ag - As_tot) + fy * As_tot)/1000  # Eq. 22.4.2.2
print(f'Axial compressive strength Pn ={Po: .2f} kN')

fi = 0.65  # Strength reduction factor for axial load 

# Nominal axial compressive strength
Pn_max = fi * alpha * Po  # Nominal axial compressive strength (in kN) 
print(f'Nominal axial compressive strength Pn ={Po: .2f} kN')

# Yield strain of the steel reinforcement
eps_y = fy / Es
print(f"Yield strain of the steel reinforcement eps_y={eps_y: .5f}, 'mm/mm'")


# Function to calculate points for interaction diagram 
def calculate_interaction_points(b, h, Pn_max, eps_y, fc, fy, Es, As_v, dis_top):

    ######### Z ###########
    # Generate Z values for the interaction diagram
    Z_values1 = np.linspace(0.1, 1, 20).tolist()    # Compresion-controled
    Z_values2 = np.linspace(-1, 0.1, 10).tolist()    
    Z_values4 = np.linspace(-2.5, -1.1, 5).tolist() # Translation zone 
    Z_values5 = np.linspace(-10, -2.49, 1000).tolist()   # Tension-controled
    Z_values6 = np.linspace(-1000, -10, 10).tolist()   #Pure tension

    Z_values = Z_values1 + Z_values2 + Z_values4 + Z_values5 + Z_values6

    # Esuring that Z has printing points
    
    Z_print = [-1000, -2.5, -1, 0.001, 1]

    for z in Z_print:
        if z not in Z_values:
            Z_values.append(z)

    # Sorting Z values from -1000 to 1
    Z_values = sorted(Z_values)

    #Function that will be used to calculate β1 based on ACI 318-19 Table 22.2.2.4.3
    def beta1(f_c):
        if f_c <= 28:
            return 0.85
        elif f_c > 28 and f_c <= 55:
            return 0.85 - 0.05 * (f_c - 28) / 7
        elif f_c > 55:
            return 0.65
    
    ######## POINTS ########
    # Lists to store results 
    Mn_points = []
    Pn_points = []
    Z_labels = []
    eps_values = []
    fs_values = []
    Fs_values = []
    Mn_bon = []
    Pn_bon = []
    Z_bon = []

    for Z in Z_values:
        # 0. Clear previous values
        eps_values.clear()
        fs_values.clear()
        Fs_values.clear()

        # 1. Strain in top reinforcement (extreme tension)
        eps_s1 = Z * eps_y 

        # 2. Neutral axis depth (similar triangles)
        try:
            c = dis_top[0] * 0.003 / (0.003 - eps_s1)
        except ZeroDivisionError:
            print("Skipped Z due to division by zero in neutral axis calc.")
            continue

        # 3. Calcualate value of eps_i for each bar row
        for di in dis_top:
            eps_i = 0.003*(c-di) / c
            eps_values.append(eps_i)

        # 4. Calculate the value of β1 based on ACI 318-19 Table
        b1 = beta1(fc)
        # 5. Equivalent stress block depth
        a = min(b1 * c, h) # Depth of the equivalent stress block (mm)

        # 6. Calculate the value of fs_i for each bar row
        for eps_i in eps_values:
            fs_i = max(-fy, min(eps_i * Es, fy))
            fs_values.append(fs_i)

        # Calculate steel forces 
        for i in range(len(dis_top)):
            As_i = As_v[i]  # Area of the i-th bar row
            fs_i = fs_values[i]  # Stress in the i-th bar row
            di = dis_top[i]  # Vertical position of the i-th bar row

            if c > di:
                Fs_i = (fs_i-0.85*fc) * As_i / 1000
                Fs_values.append(Fs_i)
            elif c < di:
                Fs_i = fs_i * As_i / 1000
                Fs_values.append(Fs_i)
            else:
                print("Invalid condition for Fs1 and Fs2 calculation.")

        # 7. Calculate Cc concrete compressive force
        Cc = (0.85 * fc * a * b)/1000  # Concrete compressive force (kN)

        # 8. Calculate Pn force
        Pn = Cc + sum(Fs_values)  # Nominal axial compressive strength (kN)

        # 9. Calculate Mn moment
        # Moment arms relative to section centroid (h/2)
        arm_Cc  = h/2 - a/2     # Cc acts at center of a
        arm_Fs = [h/2 - di for di in dis_top]  # Fs acts at the center of each bar row

        # Nominal moment
        Mn = (Cc * arm_Cc + sum([Fs_i * arm_Fs_i for Fs_i, arm_Fs_i in zip(Fs_values, arm_Fs)]))/1000  # Nominal moment (kNm)

        if 0.002 < abs(eps_s1) < 0.005 : # According to ACI 318-19, Table 21.2.2
            # Calculate strenght reduction factor
            fi = 0.65 + 0.25 * (abs(eps_s1) - 0.002) / 0.003
        elif abs(eps_s1) >= 0.005:
            fi = 0.90
        else:
            fi = 0.65

        # Points on the interaction diagram
        Pp = min(fi * Pn, Pn_max)  # Reduced axial load (kN)
        Mp = fi * Mn  # Reduced moment (kNm)

        Mn_points.append(Mp)
        Pn_points.append(Pp)
        Z_labels.append(Z)

        if Z in Z_print:
            Mn_bon.append(Mp)
            Pn_bon.append(Pp)
            Z_bon.append(f"{Z:.1f}")
        

    return Pn_points, Mn_points, Mn_bon, Pn_bon, Z_bon, Z_labels

Pn_points_v, Mn_points_v, Mn_bon_v, Pn_bon_v, Z_bon_v, Z_labels_v = calculate_interaction_points(b, h, Pn_max, eps_y, fc, fy, Es, As_v, dis_top)
Pn_points_h, Mn_points_h, Mn_bon_h, Pn_bon_h, Z_bon_h , Z_labels_h= calculate_interaction_points(h, b, Pn_max, eps_y, fc, fy, Es, As_h, dis_left)

# Points to excel 
df_points_v_all = pd.DataFrame({
    'Zv': Z_labels_v,
    'Mn (kNm)': Mn_points_v,
    'Pn (kN)': Pn_points_v})

# Points to excel 
df_points_h_all = pd.DataFrame({
    'Zv': Z_labels_h,
    'Mn (kNm)': Mn_points_h,
    'Pn (kN)': Pn_points_h})


def find_Z_where_Pn_is_zero(Pn_points, Mn_points, Z_labels):
    # Find the index where Pn_points is closest to zero
    index = np.argmin(np.abs(np.array(Pn_points)))
    Z_value = Z_labels[index]
    Mn_value = Mn_points[index]
    Pn_value = Pn_points[index]
    return Z_value, Mn_value, Pn_value

# Find Z where Pn is zero
Z_zero_v, Mn_zero_v, Pn_zero_v = find_Z_where_Pn_is_zero(Pn_points_v, Mn_points_v, Z_labels_v)
Z_zero_h, Mn_zero_h, Pn_zero_h = find_Z_where_Pn_is_zero(Pn_points_h, Mn_points_h, Z_labels_h)

# Appemd the Z=0.0 point to the list of boundary points
Mn_bon_v.append(Mn_zero_v)
Pn_bon_v.append(Pn_zero_v)
Z_bon_v.append(f"{Z_zero_v:.2f}")

Mn_bon_h.append(Mn_zero_h)
Pn_bon_h.append(Pn_zero_h)
Z_bon_h.append(f"{Z_zero_h:.2f}")


# Create a dataframe for the points
df_bon_points_v = pd.DataFrame({
    'Zv': Z_bon_v,
    'Mn (kNm)': Mn_bon_v,
    'Pn (kN)': Pn_bon_v
})
df_bon_points_h = pd.DataFrame({
    'Zh': Z_bon_h,
    'Mn (kNm)': Mn_bon_h,
    'Pn (kN)': Pn_bon_h
})


### Plotting the interaction diagram
def plot_interaction_diagram(Pn_points, Mn_points, Mn_bon, Pn_bon, color, Z_bon, show_points=False, extra_Mn=None, extra_Pn=None):
    plt.plot(Mn_points, Pn_points, '-', label="Interaction Curve", color=color, linewidth=2)
  
    for x, y, label in zip(Mn_bon, Pn_bon, Z_bon):
        plt.text(x + 5, y + 5, label, fontsize=5,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

    if show_points:
        plt.plot(Mn_points, Pn_points, '', color=color)
    
    if extra_Mn and extra_Pn:
        plt.plot(extra_Mn, extra_Pn, 'o', label='Excel Points', markersize=3)  # black squares
        for x, y in zip(extra_Mn, extra_Pn):
            plt.text(x, y, f'{x:.1f}, {y:.1f}', fontsize=6)

    plt.axhline(0, color='gray', linestyle='--')
    plt.axvline(0, color='gray', linestyle='--')
    plt.xlabel('φMn (kN-m)')
    plt.ylabel('φPn (kN)')
    plt.title('ACI 318-19 Interaction Diagram')
    plt.grid(True) # Major grid
    plt.minorticks_on()
    plt.grid(which='minor', linestyle=':', linewidth=0.5, color='gray')
    plt.legend()
    plt.tight_layout()


st.markdown("#### Bending about the strong axis - Red Reinforcement")

### Import data from Excel file -  Major reinforcement
uploaded_file1 = st.file_uploader("Upload Excel file with points", type=["xlsx"], key="1")

if uploaded_file1 is not None:
    df_points1 = pd.read_excel(uploaded_file1)
    if {'Mu', 'Pu'}.issubset(df_points1.columns):
        Mn_extra = df_points1['Mu'].tolist()
        Pn_extra = df_points1['Pu'].tolist()
    else:
        st.error("Excel must contain 'Mu' and 'Pu' columns")
        Mn_extra = []
        Pn_extra = []
else:
    Mn_extra = []
    Pn_extra = []

# Add checkbox and call the function
add_excel_points1 = st.checkbox("Show points from Excel", key="2")

fig1 = plt.figure()
plot_interaction_diagram(
    Pn_points_v, Mn_points_v,
    Mn_bon_v, Pn_bon_v, 'red',
    Z_bon_v,
    show_points=True,
    extra_Mn=Mn_extra if add_excel_points1 else None,
    extra_Pn=Pn_extra if add_excel_points1 else None
)
st.pyplot(fig1)
buf1 = BytesIO()
fig1.savefig(buf1, format="png")
buf1.seek(0)


df_bon_points_v["Zv"] = df_bon_points_v["Zv"].astype(float)
df_bon_points_h["Zh"] = df_bon_points_h["Zh"].astype(float)

df_bon_points_v = df_bon_points_v.sort_values("Zv")
df_bon_points_h = df_bon_points_h.sort_values("Zh")

df_bon_points_v = df_bon_points_v.reset_index(drop=True)
df_bon_points_h = df_bon_points_h.reset_index(drop=True)

# Add explanation for points on diagram
with st.expander("ℹ️ Boundary points explanation - Strond axis"):
    st.dataframe(df_bon_points_v)
    st.markdown(f""" 
            - Z = 1.0 - Compression controlled failure
            - Z = 0.0 - Decompression 
            - Z = -1.0 - Balance point (Compresion controled limit Strain)
            - Z = -2.5 - Tension controlled limit
            - Z = {Z_zero_v: .2f} - Pure Bending 
            - Z = -1000 - Pure tension
                            """) 

st.download_button(
    label="📥 Download Strong Axis Diagram (PNG)",
    data=buf1,
    file_name="strong_axis_interaction_diagram.png",
    mime="image/png"
)

# Convert DataFrame to Excel in-memory - Major axis
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_points_v_all.to_excel(writer, index=False, sheet_name='VRP')
output.seek(0)

# Download button
st.download_button(
    label="📥 Download Interaction Points (Excel) - S",
    data=output,
    file_name="interaction_points_major.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


st.markdown("### Bending about the weak axis - Blue Reinforcement")
### Import data from Excel file -  Minor reinforcement
uploaded_file2 = st.file_uploader("Upload Excel file with points", type=["xlsx"], key="3")


if uploaded_file2 is not None:
    df_points2 = pd.read_excel(uploaded_file2)
    if {'Mu', 'Pu'}.issubset(df_points2.columns):
        Mn_extra = df_points2['Mu'].tolist()
        Pn_extra = df_points2['Pu'].tolist()
    else:
        st.error("Excel must contain 'Mu' and 'Pu' columns")
        Mn_extra = []
        Pn_extra = []
else:
    Mn_extra = []
    Pn_extra = []

# Add checkbox and call the function
add_excel_points2 = st.checkbox("Show points from Excel", key="4")

fig2 = plt.figure()
plot_interaction_diagram(
    Pn_points_h, Mn_points_h,
    Mn_bon_h, Pn_bon_h, 'Blue',
    Z_bon_h,
    show_points=True,
    extra_Mn=Mn_extra if add_excel_points2 else None,
    extra_Pn=Pn_extra if add_excel_points2 else None
)
st.pyplot(fig2)

# Add explanation for points on diagram
with st.expander("ℹ️ Boundary points explanation - Weak axis"):
    st.dataframe(df_bon_points_h)
    st.markdown(f""" 
        - Z = 1.0 - Compression controlled failure
        - Z = 0.0 - Decompression 
        - Z = -1.0 - Balance point (Compresion controled limit Strain)
        - Z = -2.5 - Tension controlled limit
        - Z = {Z_zero_h: .2f} - Pure Bending 
        - Z = -1000 - Pure tension
                        """) 


# Save fig2 to buffer
buf2 = BytesIO()
fig2.savefig(buf2, format="png")
buf2.seek(0)

st.download_button(
    label="📥 Download Weak Axis Diagram (PNG)",
    data=buf2,
    file_name="weak_axis_interaction_diagram.png",
    mime="image/png" 
)

# Convert DataFrame to Excel in-memory - Major axis
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_points_h_all.to_excel(writer, index=False, sheet_name='HRP')
output.seek(0)

# Download button
st.download_button(
    label="📥 Download Interaction Points (Excel) - W",
    data=output,
    file_name="interaction_points_major.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


st.markdown("""
### References & Notes
    """)

st.markdown("""
    - ACI 318-19, "Building Code Requirements for Structural Concrete and Commentary"
    - E702.9-22, "Design of Concrete Structures - Reinforced Rectangular Concrete Column Interaction Diagram Example"
    - 314R_16, "Guide to Simplified Design of RC Buildings
    """)

st.markdown("""
    - [GitHub Repository]( https://github.com/EldainElf/column-interaction-curve-app)
    - [LinkedIn](https://www.linkedin.com/in/filip-m123/)
    - [E-Mail](mailto:white.wulf4@gmail.com)
            """)

if st.sidebar.button("Support the Developer!"):
    st.sidebar.write("Thank you wooo-ho-man!😊")

