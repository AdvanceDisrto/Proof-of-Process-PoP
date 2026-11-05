"""Simplified equilibrium and energy bookkeeping; not a structural solver."""
from dataclasses import dataclass
from math import pi, sqrt, ceil, isfinite

MU = 3.986004418e14
EARTH_RADIUS = 6_371_000.0
TNT_TON_J = 4.184e9

@dataclass(frozen=True)
class RingScenario:
    altitude_m: float = 500_000.0
    rotor_mass_kg: float = 180_000_000.0
    stator_mass_kg: float = 180_000_000.0
    rotor_speed_m_s: float = 10_000.0

    def __post_init__(self):
        vals=(self.altitude_m,self.rotor_mass_kg,self.stator_mass_kg,self.rotor_speed_m_s)
        if not all(isfinite(x) for x in vals) or self.altitude_m<=0 or self.rotor_mass_kg<=0 or self.stator_mass_kg<0 or self.rotor_speed_m_s<0:
            raise ValueError('finite nonnegative physical values required')
    @property
    def radius_m(self):return EARTH_RADIUS+self.altitude_m
    @property
    def circumference_m(self):return 2*pi*self.radius_m
    @property
    def circular_speed_m_s(self):return sqrt(MU/self.radius_m)
    @property
    def gravitational_force_n(self):return MU*(self.rotor_mass_kg+self.stator_mass_kg)/self.radius_m**2
    @property
    def centrifugal_proxy_n(self):return self.rotor_mass_kg*self.rotor_speed_m_s**2/self.radius_m
    @property
    def excess_radial_force_n(self):return self.centrifugal_proxy_n-self.gravitational_force_n
    @property
    def rotor_kinetic_j(self):return .5*self.rotor_mass_kg*self.rotor_speed_m_s**2
    @property
    def max_stator_mass_proxy_kg(self):return self.rotor_mass_kg*(self.rotor_speed_m_s**2*self.radius_m/MU-1)
    def to_dict(self):
        return dict(altitude_km=self.altitude_m/1000,circumference_km=self.circumference_m/1000,
                    rotor_mass_t=self.rotor_mass_kg/1000,circular_speed_kms=self.circular_speed_m_s/1000,
                    rotor_kinetic_j=self.rotor_kinetic_j,
                    rotor_energy_megatons_tnt=self.rotor_kinetic_j/(TNT_TON_J*1e6),
                    excess_radial_force_n=self.excess_radial_force_n,
                    radial_equilibrium_proxy=self.excess_radial_force_n>=0,
                    max_stator_mass_proxy_t=self.max_stator_mass_proxy_kg/1000,
                    limitations=['NOT structural stability or resilience proof','NO tensile/thermal/vacuum/rotation model',
                                 'NO containment or control model'])

def exact_potential_lift_energy_j(payload_mass_kg:float, altitude_m:float=500_000.):
    if payload_mass_kg<0 or altitude_m<0:raise ValueError('invalid mass or altitude')
    return payload_mass_kg*MU*(1/EARTH_RADIUS-1/(EARTH_RADIUS+altitude_m))

def bootstrap_model(line_density_kg_m=.025,payload_capacity_t=100,flight_price_usd=20_000_000):
    if line_density_kg_m<=0 or payload_capacity_t<=0 or flight_price_usd<0:
        raise ValueError('invalid parameters')
    ring=RingScenario();wire_t=ring.circumference_m*line_density_kg_m/1000
    components={'pilot_wire_t':wire_t,'maglev_modules_t':200.,'welding_robots_t':50.,
                'assembly_equipment_t':50.,'spares_t':100.}
    total=sum(components.values())
    return {'assumptions':{'density_kg_per_m':line_density_kg_m,'cargo_per_flight_t':payload_capacity_t,
                           'price_per_flight_usd':flight_price_usd,'capacity_proven':False,
                           'launch_schedule_verified':False},'components_t':components,'total_t':total,
            'optimistic_pooled_cargo_flights':ceil(total/payload_capacity_t),
            'separately_rounded_flights':sum(ceil(x/payload_capacity_t) for x in components.values()),
            'pooled_launch_cost_usd':ceil(total/payload_capacity_t)*flight_price_usd,
            'status':'ILLUSTRATIVE_NOT_FLIGHT_MANIFEST'}

def impact_energy_j(mass_kg,speed_m_s):
    if mass_kg<0 or speed_m_s<0:raise ValueError('invalid inputs')
    return .5*mass_kg*speed_m_s**2

def ideal_delta_kinetic_energy_j(payload_kg:float,initial_speed_m_s:float,final_speed_m_s:float):
    vals=(payload_kg,initial_speed_m_s,final_speed_m_s)
    if not all(isfinite(x) and x>=0 for x in vals):raise ValueError('invalid inputs')
    if final_speed_m_s<initial_speed_m_s:raise ValueError('expects acceleration case')
    return .5*payload_kg*(final_speed_m_s**2-initial_speed_m_s**2)

def ideal_average_power_w(energy_j:float,duration_s:float,efficiency:float=1.0):
    if not all(map(isfinite,(energy_j,duration_s,efficiency))) or energy_j<0 or duration_s<=0 or not 0<efficiency<=1:
        raise ValueError('invalid inputs')
    return energy_j/(duration_s*efficiency)
