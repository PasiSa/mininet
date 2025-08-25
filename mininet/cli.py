"""
A simple command-line interface for Mininet.

The Mininet CLI provides a simple control console which
makes it easy to talk to nodes. For example, the command

mininet> h27 ifconfig

runs 'ifconfig' on host h27.

Having a single console rather than, for example, an xterm for each
node is particularly convenient for networks of any reasonable
size.

The CLI automatically substitutes IP addresses for node names,
so commands like

mininet> h2 ping h3

should work correctly and allow host h2 to ping host h3

Several useful commands are provided, including the ability to
list all nodes ('nodes'), to print out the network topology
('net') and to check connectivity ('pingall', 'pingpair')
and bandwidth ('iperf'.)
"""

from subprocess import call
from cmd import Cmd
from os import isatty
from select import poll, POLLIN
import select
import errno
import sys
import time
import os
import atexit

from mininet.log import info, output, error
from mininet.term import makeTerms, runX11
from mininet.util import ( quietRun, dumpNodeConnections,
                           dumpPorts )

class CLI( Cmd ):
    "Simple command-line interface to talk to nodes."

    prompt = 'mininet> '

    def __init__( self, mininet, stdin=sys.stdin, script=None,
                  **kwargs ):
        """Start and run interactive or batch mode CLI
           mininet: Mininet network object
           stdin: standard input for CLI
           script: script to run in batch mode"""
        self.mn = mininet
        # Local variable bindings for py command
        self.locals = { 'net': mininet }
        # Attempt to handle input
        self.inPoller = poll()
        self.inPoller.register( stdin )
        self.inputFile = script
        Cmd.__init__( self, stdin=stdin, **kwargs )
        info( '*** Starting CLI:\n' )

        if self.inputFile:
            self.do_source( self.inputFile )
            return

        self.initReadline()
        self.run()

    readlineInited = False

    @classmethod
    def initReadline( cls ):
        "Set up history if readline is available"
        # Only set up readline once to prevent multiplying the history file
        if cls.readlineInited:
            return
        cls.readlineInited = True
        try:
            # pylint: disable=import-outside-toplevel
            from readline import ( read_history_file, write_history_file,
                                   set_history_length )
        except ImportError:
            pass
        else:
            history_path = os.path.expanduser( '~/.mininet_history' )
            if os.path.isfile( history_path ):
                read_history_file( history_path )
                set_history_length( 1000 )

            def writeHistory():
                "Write out history file"
                try:
                    write_history_file( history_path )
                except IOError:
                    # Ignore probably spurious IOError
                    pass
            atexit.register( writeHistory )

    def run( self ):
        "Run our cmdloop(), catching KeyboardInterrupt"
        while True:
            try:
                # Make sure no nodes are still waiting
                for node in self.mn.values():
                    while node.waiting:
                        info( 'stopping', node, '\n' )
                        node.sendInt()
                        node.waitOutput()
                if self.isatty():
                    quietRun( 'stty echo sane intr ^C' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                # Output a message - unless it's also interrupted
                # pylint: disable=broad-except
                try:
                    output( '\nInterrupt\n' )
                except Exception:
                    pass
                # pylint: enable=broad-except

    def emptyline( self ):
        "Don't repeat last command when you hit return."
        pass

    def getLocals( self ):
        "Local variable bindings for py command"
        self.locals.update( self.mn )
        return self.locals

    def precmd( self, line ):
        "allow for comments in the cli"
        if '#' in line:
            line = line.split( '#' )[ 0 ]
        return line

    # ==========================================================================
    # HELP AND INFORMATION COMMANDS
    # ==========================================================================

    helpStr = (
        'You may also send a command to a node using:\n'
        '  <node> command {args}\n'
        'For example:\n'
        '  mininet> h1 ifconfig\n'
        '\n'
        'The interpreter automatically substitutes IP addresses\n'
        'for node names when a node is the first arg, so commands\n'
        'like\n'
        '  mininet> h2 ping h3\n'
        'should work.\n'
        '\n'
        'Some character-oriented interactive commands require\n'
        'noecho:\n'
        '  mininet> noecho h2 vi foo.py\n'
        'However, starting up an xterm/gterm is generally better:\n'
        '  mininet> xterm h2\n\n'
    )

    def do_help( self, line ):  # pylint: disable=arguments-renamed
        "Describe available CLI commands."
        Cmd.do_help( self, line )
        if line == '':
            output( self.helpStr )

    def do_nodes( self, _line ):
        "List all nodes."
        nodes = ' '.join( sorted( self.mn ) )
        output( 'available nodes are: \n%s\n' % nodes )

    def do_ports( self, _line ):
        "display ports and interfaces for each switch"
        dumpPorts( self.mn.switches )

    def do_net( self, _line ):
        "List network connections."
        dumpNodeConnections( self.mn.values() )

    def do_intfs( self, _line ):
        "List interfaces."
        for node in self.mn.values():
            output( '%s: %s\n' %
                    ( node.name, ','.join( node.intfNames() ) ) )

    def do_dump( self, _line ):
        "Dump node info."
        for node in self.mn.values():
            output( '%s\n' % repr( node ) )

    def do_links( self, _line ):
        "Report on links"
        for link in self.mn.links:
            output( link, link.status(), '\n' )

    # ==========================================================================
    # NETWORK TESTING COMMANDS
    # ==========================================================================

    def do_pingall( self, line ):
        "Ping between all hosts."
        self.mn.pingAll( line )

    def do_pingpair( self, _line ):
        "Ping between first two hosts, useful for testing."
        self.mn.pingPair()

    def do_pingallfull( self, _line ):
        "Ping between all hosts, returns all ping results."
        self.mn.pingAllFull()

    def do_pingpairfull( self, _line ):
        "Ping between first two hosts, returns all ping results."
        self.mn.pingPairFull()

    # ==========================================================================
    # PERFORMANCE TESTING COMMANDS
    # ==========================================================================

    def do_iperf( self, line ):
        """Simple iperf TCP test between two (optionally specified) hosts.
           Usage: iperf node1 node2"""
        args = line.split()
        if not args:
            self.mn.iperf()
        elif len(args) == 2:
            hosts = []
            err = False
            for arg in args:
                if arg not in self.mn:
                    err = True
                    error( "node '%s' not in network\n" % arg )
                else:
                    hosts.append( self.mn[ arg ] )
            if not err:
                self.mn.iperf( hosts )
        else:
            error( 'invalid number of args: iperf src dst\n' )

    def do_iperfudp( self, line ):
        """Simple iperf UDP test between two (optionally specified) hosts.
           Usage: iperfudp bw node1 node2"""
        args = line.split()
        if not args:
            self.mn.iperf( l4Type='UDP' )
        elif len(args) == 3:
            udpBw = args[ 0 ]
            hosts = []
            err = False
            for arg in args[ 1:3 ]:
                if arg not in self.mn:
                    err = True
                    error( "node '%s' not in network\n" % arg )
                else:
                    hosts.append( self.mn[ arg ] )
            if not err:
                self.mn.iperf( hosts, l4Type='UDP', udpBw=udpBw )
        else:
            error( 'invalid number of args: iperfudp bw src dst\n' +
                   'bw examples: 10M\n' )

    # ==========================================================================
    # LINK MANAGEMENT COMMANDS
    # ==========================================================================

    def do_link( self, line ):
        """Bring link(s) between two nodes up or down.
           Usage: link node1 node2 [up/down]"""
        args = line.split()
        if len(args) != 3:
            error( 'invalid number of args: link end1 end2 [up down]\n' )
        elif args[ 2 ] not in [ 'up', 'down' ]:
            error( 'invalid type: link end1 end2 [up down]\n' )
        else:
            self.mn.configLinkStatus( *args )

    def do_addlink(self, line):
        """Add a link between two nodes with custom parameters.
        Usage: addlink node1 node2 [bw=X] [delay=Xms] [loss=X%]
               [max_queue_size=X]

        Examples:
            addlink h1 s1                    # Basic link with defaults
            addlink h1 s1 bw=10              # 10 Mbps bandwidth
            addlink h1 s1 bw=100 delay=5ms   # 100 Mbps with 5ms delay
            addlink h1 s1 loss=1 bw=50       # 1% loss rate, 50 Mbps

        Parameters:
            bw: bandwidth in Mbps (e.g., bw=10)
            delay: propagation delay (e.g., delay=10ms)
            loss: packet loss percentage (e.g., loss=2)
            max_queue_size: maximum queue size (e.g., max_queue_size=100)

        Note: Requires TCLink to be enabled for traffic control parameters.
        """
        args = line.split()
        if len(args) < 2:
            error('Usage: addlink node1 node2 [parameters]\n')
            return

        node1_name, node2_name = args[0], args[1]

        # Validate nodes exist
        validation_error = self._validate_nodes(node1_name, node2_name)
        if validation_error:
            error(validation_error)
            return

        node1 = self.mn.nameToNode[node1_name]
        node2 = self.mn.nameToNode[node2_name]

        # Check for existing links
        if self.mn.linksBetween(node1, node2):
            error(f'Link already exists between {node1_name} and '
                  f'{node2_name}\n')
            return

        # Parse parameters
        params, parse_error = self._parse_link_params(args[2:])
        if parse_error:
            error(parse_error)
            return

        # Add the link
        self._add_link_with_config(node1, node2, params)

    def do_updatelink(self, line):
        """Update parameters of an existing link between two nodes.
        Usage: updatelink node1 node2 [bw=X] [delay=Xms] [loss=X%]
               [max_queue_size=X]

        Examples:
            updatelink h1 s1 bw=50           # Change bandwidth to 50 Mbps
            updatelink h1 s1 delay=20ms      # Update delay to 20ms
            updatelink h1 h2 bw=100 loss=1   # Update bandwidth and loss
            updatelink h2 h3 delay=5ms loss=0 # Update delay, remove loss

        Parameters:
            bw: bandwidth in Mbps (e.g., bw=10)
            delay: propagation delay (e.g., delay=10ms)
            loss: packet loss percentage (e.g., loss=2)
            max_queue_size: maximum queue size (e.g., max_queue_size=100)

        Note: Requires TCLink to be enabled for traffic control parameters.
        """
        args = line.split()
        if len(args) < 3:
            error('Usage: updatelink node1 node2 [parameters]\n')
            return

        node1_name, node2_name = args[0], args[1]

        # Validate nodes exist
        validation_error = self._validate_nodes(node1_name, node2_name)
        if validation_error:
            error(validation_error)
            return

        node1 = self.mn.nameToNode[node1_name]
        node2 = self.mn.nameToNode[node2_name]

        # Find existing link
        existing_links = self.mn.linksBetween(node1, node2)
        if not existing_links:
            error(f'No link found between {node1_name} and {node2_name}\n')
            return

        # Parse parameters
        params, parse_error = self._parse_link_params(args[2:])
        if parse_error:
            error(parse_error)
            return

        if not params:
            error('No parameters provided for update\n')
            return

        # Update the link
        self._update_link_config(node1_name, node2_name,
                                 existing_links[0], params)

    def _validate_nodes(self, node1_name, node2_name):
        """Validate that both nodes exist in the network."""
        if node1_name not in self.mn.nameToNode:
            return f'Node {node1_name} not found\n'
        if node2_name not in self.mn.nameToNode:
            return f'Node {node2_name} not found\n'
        return None

    def _parse_link_params(self, param_args):
        """Parse link parameters from command arguments."""
        params = {}

        for arg in param_args:
            if '=' not in arg:
                continue

            key, value = arg.split('=', 1)
            param_value, parse_error = self._parse_single_param(key, value)

            if parse_error:
                return None, parse_error

            params[key] = param_value

        return params, None

    def _parse_single_param(self, key, value):
        """Parse a single parameter key-value pair."""
        try:
            if key == 'bw':
                return float(value), None
            elif key == 'delay':
                return value, None  # Keep as string (e.g., '10ms')
            elif key == 'loss':
                return float(value), None
            elif key == 'max_queue_size':
                return int(value), None
            else:
                return value, None  # Other parameters as strings
        except ValueError:
            return None, f'Invalid {key} value: {value}\n'

    def _add_link_with_config(self, node1, node2, params):
        """Add link and configure interfaces if needed."""
        try:
            link = self.mn.addLink(node1, node2, **params)
            output(f'Added link between {node1.name} and {node2.name}\n')

            # Configure host-to-host links
            self._configure_host_interfaces(node1, node2, link)

        except (AttributeError, ValueError, KeyError) as e:
            error(f'Failed to add link: {str(e)}\n')

    def _configure_host_interfaces(self, node1, node2, link):
        """Configure interfaces for direct host-to-host links."""
        if not (hasattr(node1, 'setIP') and hasattr(node2, 'setIP')):
            return

        node1_name = node1.name
        node2_name = node2.name

        if not (node1_name.startswith('h') and node2_name.startswith('h')):
            return

        try:
            h1_num = int(node1_name[1:])
            h2_num = int(node2_name[1:])

            # Use point-to-point subnet
            subnet_base = f'192.168.{min(h1_num, h2_num)}{max(h1_num, h2_num)}'
            ip1 = f'{subnet_base}.1/30'
            ip2 = f'{subnet_base}.2/30'

            node1.setIP(ip1, intf=link.intf1)
            node2.setIP(ip2, intf=link.intf2)

            output(f'Configured {node1_name} interface with {ip1}\n')
            output(f'Configured {node2_name} interface with {ip2}\n')

        except (ValueError, AttributeError):
            # Fall back to default behavior if configuration fails
            pass

    def _update_link_config(self, node1_name, node2_name, link, params):
        """Update link configuration with new parameters."""
        try:
            # Configure both interfaces of the link
            results = []

            # Update interface 1 (if it supports traffic control)
            if hasattr(link.intf1, 'config'):
                result1 = link.intf1.config(**params)
                results.append(f"intf1: {result1}")

            # Update interface 2 (if it supports traffic control)
            if hasattr(link.intf2, 'config'):
                result2 = link.intf2.config(**params)
                results.append(f"intf2: {result2}")

            if not results:
                error(f'Link between {node1_name} and {node2_name} does not '
                        ' support traffic control parameters\n')
                output('Note: Use TCLink when creating the topology to enable '
                        'traffic control\n')
                return

            # Format parameter display
            param_str = ', '.join([f'{k}={v}' for k, v in params.items()])
            output(f'Updated link between {node1_name} and {node2_name} '
                   f'with {param_str}\n')

        except (AttributeError, ValueError, KeyError) as e:
            error(f'Failed to update link: {str(e)}\n')
        except (OSError, RuntimeError) as e:
            # Handle cases where config() might fail for system-level reasons
            error(f'Error updating link parameters: {str(e)}\n')
            output('Note: Some parameters may require recreating the link or '
                   'using TCLink\n')

    def do_removelink(self, line):
        """Remove a link between two nodes.
        Usage: removelink node1 node2

        Examples:
            removelink h1 s1    # Remove link between h1 and s1
            removelink h2 h3    # Remove link between h2 and h3

        Note: This will remove the first link found between the nodes.
        """
        args = line.split()
        if len(args) != 2:
            error('Usage: removelink node1 node2\n')
            return

        node1_name, node2_name = args[0], args[1]

        # Validate nodes exist
        validation_error = self._validate_nodes(node1_name, node2_name)
        if validation_error:
            error(validation_error)
            return

        node1 = self.mn.nameToNode[node1_name]
        node2 = self.mn.nameToNode[node2_name]

        # Find existing link
        existing_links = self.mn.linksBetween(node1, node2)
        if not existing_links:
            error(f'No link found between {node1_name} and {node2_name}\n')
            return

        # Remove the link
        link = existing_links[0]
        try:
            # Properly delete the link using Mininet's built-in method
            if hasattr(link, 'delete'):
                link.delete()
            else:
                # Fallback: manually clean up interfaces
                if hasattr(link, 'intf1') and link.intf1:
                    # Delete the actual interface before removing from node
                    if hasattr(link.intf1, 'delete'):
                        link.intf1.delete()
                    node1.delIntf(link.intf1)

                if hasattr(link, 'intf2') and link.intf2:
                    # Delete the actual interface before removing from node
                    if hasattr(link.intf2, 'delete'):
                        link.intf2.delete()
                    node2.delIntf(link.intf2)

            # Remove link from network
            if link in self.mn.links:
                self.mn.links.remove(link)

            output(f'Removed link between {node1_name} and {node2_name}\n')

        except (AttributeError, ValueError) as e:
            error(f'Failed to remove link: {str(e)}\n')
        except (OSError, RuntimeError) as e:
            error(f'System error removing link: {str(e)}\n')

    def complete_updatelink(self, text, line, _begidx, _endidx):
        """Auto-completion for updatelink command."""
        args = line.split()

        # Complete node names for first two arguments
        if len(args) <= 3 and not text.startswith((
                'bw=', 'delay=', 'loss=', 'max_queue_size=')):
            nodes = list(self.mn.nameToNode.keys())
            return [node for node in nodes if node.startswith(text)]

        # Complete parameter names
        params = ['bw=', 'delay=', 'loss=', 'max_queue_size=']
        if '=' in text:
            return []
        return [p for p in params if p.startswith(text)]

    # ==========================================================================
    # TERMINAL AND X11 COMMANDS
    # ==========================================================================

    def do_xterm( self, line, term='xterm' ):
        """Spawn xterm(s) for the given node(s).
           Usage: xterm node1 node2 ..."""
        args = line.split()
        if not args:
            error( 'usage: %s node1 node2 ...\n' % term )
        else:
            for arg in args:
                if arg not in self.mn:
                    error( "node '%s' not in network\n" % arg )
                else:
                    node = self.mn[ arg ]
                    self.mn.terms += makeTerms( [ node ], term = term )

    def do_gterm( self, line ):
        """Spawn gnome-terminal(s) for the given node(s).
           Usage: gterm node1 node2 ..."""
        self.do_xterm( line, term='gterm' )

    def do_x( self, line ):
        """Create an X11 tunnel to the given node,
           optionally starting a client.
           Usage: x node [cmd args]"""
        args = line.split()
        if not args:
            error( 'usage: x node [cmd args]...\n' )
        else:
            node = self.mn[ args[ 0 ] ]
            cmd = args[ 1: ]
            self.mn.terms += runX11( node, cmd )

    # ==========================================================================
    # PYTHON EXECUTION COMMANDS
    # ==========================================================================

    # do_py() and do_px() need to catch any exception during eval()/exec()
    # pylint: disable=broad-except

    def do_py( self, line ):
        """Evaluate a Python expression.
           Node names may be used, e.g.: py h1.cmd('ls')"""
        try:
            # pylint: disable=eval-used
            result = eval( line, globals(), self.getLocals() )
            if result is None:
                return
            elif isinstance( result, str ):
                output( result + '\n' )
            else:
                output( repr( result ) + '\n' )
        except Exception as e:
            output( str( e ) + '\n' )

    # We are in fact using the exec() pseudo-function
    # pylint: disable=exec-used

    def do_px( self, line ):
        """Execute a Python statement.
            Node names may be used, e.g.: px print h1.cmd('ls')"""
        try:
            exec( line, globals(), self.getLocals() )
        except Exception as e:
            output( str( e ) + '\n' )

    # ==========================================================================
    # SWITCH AND CONTROLLER COMMANDS
    # ==========================================================================

    def do_dpctl( self, line ):
        """Run dpctl (or ovs-ofctl) command on all switches.
           Usage: dpctl command [arg1] [arg2] ..."""
        args = line.split()
        if len(args) < 1:
            error( 'usage: dpctl command [arg1] [arg2] ...\n' )
            return
        for sw in self.mn.switches:
            output( '*** ' + sw.name + ' ' + ('-' * 72) + '\n' )
            output( sw.dpctl( *args ) )

    def do_switch( self, line ):
        "Starts or stops a switch"
        args = line.split()
        if len(args) != 2:
            error( 'invalid number of args: switch <switch name>'
                   '{start, stop}\n' )
            return
        sw = args[ 0 ]
        command = args[ 1 ]
        if sw not in self.mn or self.mn.get( sw ) not in self.mn.switches:
            error( 'invalid switch: %s\n' % args[ 1 ] )
        else:
            sw = args[ 0 ]
            command = args[ 1 ]
            if command == 'start':
                self.mn.get( sw ).start( self.mn.controllers )
            elif command == 'stop':
                self.mn.get( sw ).stop( deleteIntfs=False )
            else:
                error( 'invalid command: '
                       'switch <switch name> {start, stop}\n' )

    def do_wait( self, _line ):
        "Wait until all switches have connected to a controller"
        self.mn.waitConnected()

    # ==========================================================================
    # SYSTEM AND UTILITY COMMANDS
    # ==========================================================================

    def do_sh( self, line ):
        """Run an external shell command
           Usage: sh [cmd args]"""
        assert self  # satisfy pylint and allow override
        call( line, shell=True )

    # pylint: enable=broad-except,exec-used

    def do_noecho( self, line ):
        """Run an interactive command with echoing turned off.
           Usage: noecho [cmd args]"""
        if self.isatty():
            quietRun( 'stty -echo' )
        self.default( line )
        if self.isatty():
            quietRun( 'stty echo' )

    def do_source( self, line ):
        """Read commands from an input file.
           Usage: source <file>"""
        args = line.split()
        if len(args) != 1:
            error( 'usage: source <file>\n' )
            return
        try:
            with open( args[ 0 ] ) as self.inputFile:
                while True:
                    line = self.inputFile.readline()
                    if len( line ) > 0:
                        self.onecmd( line )
                    else:
                        break
        except IOError:
            error( 'error reading file %s\n' % args[ 0 ] )
        self.inputFile.close()
        self.inputFile = None

    def do_time( self, line ):
        "Measure time taken for any command in Mininet."
        start = time.time()
        self.onecmd(line)
        elapsed = time.time() - start
        self.stdout.write("*** Elapsed time: %0.6f secs\n" % elapsed)

    # ==========================================================================
    # EXIT COMMANDS
    # ==========================================================================

    def do_exit( self, _line ):
        "Exit"
        assert self  # satisfy pylint and allow override
        return 'exited by user command'

    def do_quit( self, line ):
        "Exit"
        return self.do_exit( line )

    def do_EOF( self, line ):
        "Exit"
        output( '\n' )
        return self.do_exit( line )

    # ==========================================================================
    # CORE CLI FUNCTIONALITY
    # ==========================================================================

    def isatty( self ):
        "Is our standard input a tty?"
        return isatty( self.stdin.fileno() )

    def default( self, line ):
        """Called on an input line when the command prefix is not recognized.
           Overridden to run shell commands when a node is the first
           CLI argument.  Past the first CLI argument, node names are
           automatically replaced with corresponding IP addrs."""

        first, args, line = self.parseline( line )

        if first in self.mn:
            if not args:
                error( '*** Please enter a command for node: %s <cmd>\n'
                       % first )
                return
            node = self.mn[ first ]
            rest = args.split( ' ' )
            # Substitute IP addresses for node names in command
            # If updateIP() returns None, then use node name
            substituted_args = []
            for arg in rest:
                if arg in self.mn:
                    target_node = self.mn[arg]
                    default_intf = target_node.defaultIntf()
                    if default_intf is not None:
                        ip = default_intf.updateIP()
                        substituted_args.append(ip or arg)
                    else:
                        error( f'*** Error: node {arg} has no interfaces - '
                               f'cannot resolve IP address\n' )
                        return
                else:
                    substituted_args.append(arg)

            rest = ' '.join( substituted_args )
            # Run cmd on node:
            node.sendCmd( rest )
            self.waitForNode( node )
        else:
            error( '*** Unknown command: %s\n' % line )

    def waitForNode( self, node ):
        "Wait for a node to finish, and print its output."
        # Pollers
        nodePoller = poll()
        nodePoller.register( node.stdout )
        bothPoller = poll()
        bothPoller.register( self.stdin, POLLIN )
        bothPoller.register( node.stdout, POLLIN )
        if self.isatty():
            # Buffer by character, so that interactive
            # commands sort of work
            quietRun( 'stty -icanon min 1' )
        while True:
            try:
                bothPoller.poll()
                # XXX BL: this doesn't quite do what we want.
                # pylint: disable=condition-evals-to-constant
                if False and self.inputFile:
                    key = self.inputFile.read( 1 )
                    if key != '':
                        node.write( key )
                    else:
                        self.inputFile = None
                # pylint: enable=condition-evals-to-constant
                if isReadable( self.inPoller ):
                    key = self.stdin.read( 1 )
                    node.write( key )
                if isReadable( nodePoller ):
                    data = node.monitor()
                    output( data )
                if not node.waiting:
                    break
            except KeyboardInterrupt:
                # There is an at least one race condition here, since
                # it's possible to interrupt ourselves after we've
                # read data but before it has been printed.
                node.sendInt()
            except select.error as e:
                # pylint: disable=unpacking-non-sequence
                # pylint: disable=unbalanced-tuple-unpacking
                errno_, errmsg = e.args
                if errno_ != errno.EINTR:
                    error( "select.error: %s, %s" % (errno_, errmsg) )
                    node.sendInt()


# Helper functions

def isReadable( poller ):
    "Check whether a Poll object has a readable fd."
    for fdmask in poller.poll( 0 ):
        mask = fdmask[ 1 ]
        if mask & POLLIN:
            return True
        return False
