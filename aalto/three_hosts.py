#!/usr/bin/env python

from mininet.topo import Topo


class ThreeHostsTopo(Topo):
    """Topology with h1, h2, h3 and minimal connectivity for proper initialization"""
    
    def build(self):
        # Add exactly 3 hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2') 
        h3 = self.addHost('h3')
        
        # Add a switch for minimal initialization (you can ignore it)
        s1 = self.addSwitch('s1')
        
        # Add minimal links just for initialization - you can add more via CLI
        # These give each host a default interface so commands work
        self.addLink(h1, s1)
        self.addLink(h2, s1) 
        self.addLink(h3, s1)

# Alternative: Completely minimal topology        
class MinimalTestTopo(Topo):
    """Just h1 and h2 with basic connectivity"""
    
    def build(self):
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        
        # One basic link so hosts can execute commands
        self.addLink(h1, h2)

class JustHostTopo(Topo):
    """Just h1 and h2 with no connectivity"""
    
    def build(self):
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')

# Register topologies
topos = {
    'threehosts': ThreeHostsTopo,
    'minimal': MinimalTestTopo,
    'justhost': JustHostTopo
}