from powersys import Network, SLACK, PV, PQ

def ieee14():
    bd = [  # id,type,Pd,Qd,Bs(MVAr),Vm,Va
     (1,SLACK,0,0,0,1.06,0),(2,PV,21.7,12.7,0,1.045,0),(3,PV,94.2,19,0,1.01,0),
     (4,PQ,47.8,-3.9,0,1,0),(5,PQ,7.6,1.6,0,1,0),(6,PV,11.2,7.5,0,1.07,0),
     (7,PQ,0,0,0,1,0),(8,PV,0,0,0,1.09,0),(9,PQ,29.5,16.6,19,1,0),
     (10,PQ,9,5.8,0,1,0),(11,PQ,3.5,1.8,0,1,0),(12,PQ,6.1,1.6,0,1,0),
     (13,PQ,13.5,5.8,0,1,0),(14,PQ,14.9,5,0,1,0)]
    net = Network()
    net.buses = [dict(id=i,type=t,pd=p,qd=q,bs=bs,vm=vm,va=va,kv=(132.0 if i<=5 else 33.0)) for i,t,p,q,bs,vm,va in bd]  # kV: illustrative
    net.gens = [dict(bus=1,pg=0,vg=1.06,xd2=0.10),dict(bus=2,pg=40,vg=1.045,qmin=-40,qmax=50,xd2=0.20),dict(bus=3,pg=0,vg=1.01,qmin=0,qmax=40,xd2=0.20),
                dict(bus=6,pg=0,vg=1.07,qmin=-6,qmax=24,xd2=0.20),dict(bus=8,pg=0,vg=1.09,qmin=-6,qmax=24,xd2=0.20)]
    br = [(1,2,.01938,.05917,.0528,0),(1,5,.05403,.22304,.0492,0),(2,3,.04699,.19797,.0438,0),
     (2,4,.05811,.17632,.034,0),(2,5,.05695,.17388,.0346,0),(3,4,.06701,.17103,.0128,0),
     (4,5,.01335,.04211,0,0),(4,7,0,.20912,0,.978),(4,9,0,.55618,0,.969),(5,6,0,.25202,0,.932),
     (6,11,.09498,.1989,0,0),(6,12,.12291,.25581,0,0),(6,13,.06615,.13027,0,0),(7,8,0,.17615,0,0),
     (7,9,0,.11001,0,0),(9,10,.03181,.0845,0,0),(9,14,.12711,.27038,0,0),(10,11,.08205,.19207,0,0),
     (12,13,.22092,.19988,0,0),(13,14,.17092,.34802,0,0)]
    net.branches = [dict(f=f,t=t,r=r,x=x,b=b,tap=tp) for f,t,r,x,b,tp in br]
    # Demo breaker ratings (illustrative) -- replace with nameplate data
    net.breakers = [
      dict(id="CB-B1",  bus=1,  rated_kv=145, rated_break_kA=25.0, rated_make_kA=65.0),
      dict(id="CB-B4",  bus=4,  rated_kv=145, rated_break_kA=25.0, rated_make_kA=65.0),
      dict(id="CB-B6",  bus=6,  rated_kv=36,  rated_break_kA=16.0, rated_make_kA=40.0),
      dict(id="CB-B8",  bus=8,  rated_kv=36,  rated_break_kA=16.0, rated_make_kA=40.0),
      dict(id="CB-B9",  bus=9,  rated_kv=36,  rated_break_kA=16.0, rated_make_kA=40.0),
      dict(id="CB-B13", bus=13, rated_kv=36,  rated_break_kA=16.0, rated_make_kA=40.0),
    ]
    return net
