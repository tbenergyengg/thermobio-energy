from shortcircuit import ShortCircuit
from breakerduty import check_breakers, print_breaker_report
from ieee14 import ieee14
net = ieee14()
print_breaker_report(check_breakers(net, ShortCircuit(net)))
