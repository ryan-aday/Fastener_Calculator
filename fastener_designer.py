### Fastener Engineering Calculator
### Notes:
# - Units are in in and psi
# - For planar joining only

### Refs:
# Shigley's Mechanical Design, 10th (See all of Chapter 8):
# https://www.mechfamily-ju.com/storage/images/files/file_1731443577xeDvd.pdf


from math import pi, atan, tan, log, cos, sqrt


### Parameters 
is_through = True;


d = 0.25; # bolt nominal diameter
TPI = 28; # threads per inch
d_h = 0.4; # Bolt head diameter [in]
bolt_head_h = 0.2; # Bolt head height [in]
bolt_E = 3e7; # Bolt Emod [psi], set to steel


w1_t = 0.0; # Washer  1 thickness [in]
w2_t = 0.0; # Washer thickness [in]
w_E = 3e7; # Washer Emod [psi], set to steel

nut_t = 0.0; # Nut thickness [in]

m1_t = 0.1; # Material 1 thickness, closest to the head of the bolt [in]
m1_E = 1e7; # Material 2 Emod [psi], set to steel

m2_t = 0.25; # Material 2 thickness [in]
m2_E = 3e7; # Material 2 Emod [psi], set to steel

N = 3; # Number of bolts
F_i = 50; # Preload [lbf]
P_total = 100; # Total external tensile load applied to joint [lbf]


P_min = 20; # Minimum force per bolt [lbf]
P_max = 40; # Maximum force per bolt [lbf]

f = 0.15; # Static friction coeff
f_c = 0.15; #Coulomb friction coeff


S_p = 120e3; # Minimum bolt proof strength [psi]
S_ut = 58e3; # Bolt ultimate tensile strength [psi]
S_e = 23.2e3; # Bolt endurance strength [psi]
#########################################################################



### Functions 

## Grip & Fastener Length
if is_through:
	l = w1_t + m1_t + m2_t + w2_t;
	L = l + nut_t;
else:
	L = h + 1.5 * d;
	if m2_t >= d:
		l = h + d/2;
	else:
		l = h + m2_t/2;


## Thread Length
if L <= 6:
	L_t = 2*d + 0.25;
else:
	L_t = 2*d + 0.5;
    
l_d = L - L_t; # Length of unthreaded portion in grip
l_t = l - l_d; # Length of threaded portion in grip
A_d = pi * d**2 / 4;
A_t = 0.7854 * (d - 0.9743/TPI)**2; # Area of UNC/UNF threaded portion
k_b = (A_d*A_t*bolt_E) / (A_d*l_t + A_t*l_d); # Bolt stiffness

## Frustum Stiffness
def frustum_stiffness(E, D, d, t, alpha):
    num = pi * E * d * tan(alpha);
    den_1 = (2*t*tan(alpha) + D - d) * (D + d);
    den_2 = (2*t*tan(alpha) + D + d) * (D - d);
    k = num / (log(den_1/den_2));
    
    return k;

alpha = atan((d_h/2) / bolt_head_h);

# Calculate material heights and lengths from frustums
 
frustum_mid_plane = l/2;
frustum_outer_diamter = (m2_t + w2_t) + 2 * (w1_t + m1_t) * tan(alpha);

if w1_t + m1_t < frustum_mid_plane:
    middle_frustum_material_t = m2_t + w2_t - frustum_mid_plane;
    middle_frustum_material_E = m2_E;
else:
    middle_frustum_material_t = w1_t + m1_t - frustum_mid_plane;
    middle_frustum_material_E = m1_E;

    
k_1 = frustum_stiffness(m1_E, d_h, d, w1_t + m1_t, alpha);
k_2 = frustum_stiffness(m2_E, d_h, d, m2_t + w2_t, alpha);

try:
    k_mid = frustum_stiffness(middle_frustum_material_E, d_h, d, middle_frustum_material_t, alpha);
    k_m = (k_1**-1 + k_mid **-1 + k_2**-1)**-1;

except:
    print("k_mid is NaN, since the frustum midpoint lies between the mate of the joined materials.")
    k_m = (k_1**-1 + k_2**-1)**-1;



print("k_b =" + str(k_b) + " [in^2/lb]")
print("k_m =" + str(k_m)+ " [in^2/lb]")


## Stiffness Joint Constant, Loads
P = P_total / N; # Tensile load per bolt
C = k_b / (k_b + k_m); # Stiffness joint constant
F_b = C * P + F_i; # Resultant bolt load
F_m = (1-C) * P - F_i; # Resultant member load


d_minor = d - 1.299038 * 1/TPI; # Minor diameter (for UNC/UNC) [in]
tan_gamma = l / (pi * d_minor)

# Torque Coefficien & Torque (should be overrideable by parameters, but this is the default)
K = (d_minor / (2 * d)) * (tan_gamma + f * (cos(alpha)**-1))/(1 - f * tan_gamma * (cos(alpha)**-1)) + 0.625 * f_c;

T = K * F_i * d; # Preload torque

## Tensile Stresses & Load Factors
S_b = (C * P + F_i)/A_t; # Bolt tensile stress [psi]
n_p = S_p * A_t / (C*P + F_i); # SF for static stress exceeding proof stress
n_l = (S_p * A_t - F_i) / (C * P); # Load factor to avoid overloading
n_0 = F_i / (P * 1-C); # Load factor against joint separation 

print("n_p =" + str(n_p))
print("n_l =" + str(n_l))
print("n_0 =" + str(n_0))



F_p = A_t * S_p; # Proof force [lbf]
print("F_p =" + str(F_p) + " [lbf]")



## Fatigue Loading
F_b_min = C * P_min + F_i;  
F_b_max = C * P_max + F_i;  

sigma_a = C * (P_max - P_min) / (2*A_t); # Alternating stress [psi]
sigma_m = C * (P_max - P_min) / (2*A_t) + F_i / A_t; # Midrange stress [psi]
sigma_i = sigma_m - sigma_a; # Preload stress [psi]


S_a = S_e * sigma_a * (S_ut - sigma_i) / (S_ut*sigma_a + S_e * (sigma_m - sigma_i)); # Alternating stress failure on Goodman line
S_m = (S_a - S_e) * -1 * (S_ut / S_e);  # Midrange stress failure on Goodman line


S_e_goodman = S_a / (1 - S_m / S_ut)  # Endurance strength, Goodman criterion [psi]
S_e_gerber = S_a / (1 - (S_m / S_ut)**2) # Endurance strength, Gerber criterion [psi]
S_e_ASME_elliptic =   S_a / sqrt((1 - (S_m / S_ut)**2)) # Endurance strength, ASME Elliptic criterion [psi]

n_f_goodman = S_e * (S_ut-sigma_i) / (sigma_a * (S_ut + S_e));  # Safety factor, ASME Elliptic criterion
n_f_gerber = (1 / (2 * sigma_a * S_e))*(S_ut * sqrt(S_ut ** 2 + 4 * S_e * (S_e + sigma_i)) - S_ut ** 2 - 2 * sigma_i * S_e) # Safety factor, Gerber criterion
n_f_ASME_elliptic = (S_e / (sigma_a * (S_p ** 2 + S_e ** 2))) * (S_p * sqrt(S_p ** 2 + S_e ** 2 - sigma_i ** 2) - sigma_i * S_e) # Safety factor, ASME Elliptic criterion

print("n_f Goodman: " + str(n_f_goodman));
print("n_f Gerber: " + str(n_f_goodman));
print("n_f ASME Elliptic: " + str(n_f_ASME_elliptic));