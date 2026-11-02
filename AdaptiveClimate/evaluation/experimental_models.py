"""Small offline thermal candidates; never imported by ESPHome runtime."""
import math


def heat_proxy(room, supply, valve, heating):
    return min(1.5,max(0,(supply-room)/50))*min(1,max(0,valve/100)) if heating else 0.0


def facade_projection(irradiance, solar_azimuth, solar_elevation, window_azimuth):
    """Directional proxy only, NOT conversion of global to direct irradiance.

    Solar geometry must be supplied; missing location is never guessed.
    """
    if solar_elevation <= 0:
        return 0.0
    return max(0,irradiance)*max(0,math.cos(math.radians(solar_elevation))*
                               math.cos(math.radians(solar_azimuth-window_azimuth)))


class Candidate:
    def __init__(self, name, tau=20, extras=()):
        self.name,self.tau,self.extras=name,tau,tuple(extras)
        self.coefficients=[0.0]*(3+len(extras))

    def features(self, row, room=None, radiator=None):
        room=row['room'] if room is None else room
        radiator=row['radiator'] if radiator is None else radiator
        x=[(row['outdoor']-room)/10,radiator,1]
        for term in self.extras:
            if row.get(term) is None:raise ValueError('Missing candidate input: '+term)
            if term=='trv': x.append((row['trv']-room)/10)
            elif term in ('solar','facade'):x.append(row[term]/1000)
            elif term=='wind':x.append(row['wind']*(row['outdoor']-room)/100)
            elif term=='vent':x.append(row['vent']*(row['outdoor']-room)/10)
        return x

    def fit(self, samples, ridge=0.01):
        """Bounded coordinate descent on one-step rate targets; deterministic."""
        n=len(self.coefficients)
        lo=[0,0,-.03]+[0 if x in ('trv','solar','wind','facade') else -.1 for x in self.extras]
        hi=[.2,.3,.03]+[.3]*len(self.extras)
        xy=[(self.features(a),y) for a,y in samples]
        if not xy:raise ValueError('Cannot fit without training samples')
        b=self.coefficients
        for _ in range(800):
            change=0
            for j in range(n):
                numerator=sum(x[j]*(y-sum(x[k]*b[k] for k in range(n) if k!=j)) for x,y in xy)
                denominator=ridge+sum(x[j]*x[j] for x,y in xy)
                updated=min(hi[j],max(lo[j],numerator/denominator))
                change=max(change,abs(updated-b[j]));b[j]=updated
            if change<1e-10:break
        return self

    def forecast(self,row,minutes):
        room,rad=row['room'],row['radiator']
        drive=heat_proxy(row['room'],row['supply'],row['valve'],row['ch'])
        for _ in range(minutes):
            rad=drive+(rad-drive)*math.exp(-1/self.tau)
            room+=sum(c*x for c,x in zip(self.coefficients,self.features(row,room,rad)))
            if not math.isfinite(room) or not -10 <= room <= 50:return None
        return room


def specifications():
    return [Candidate('radiator_5',5),Candidate('two_state_20',20),Candidate('radiator_40',40),
            Candidate('trv_20',20,('trv',)),Candidate('solar_proxy_20',20,('solar',)),
            Candidate('wind_vent_20',20,('wind','vent'))]
