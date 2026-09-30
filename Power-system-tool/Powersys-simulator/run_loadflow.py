from powersys import newton_raphson, print_report
from ieee14 import ieee14
net = ieee14()
print_report(net, newton_raphson(net))
