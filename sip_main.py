'''
Run the SIP Server sipp
./sipp -sf aseem-sipp.xml -trace_logs -trace_msg
aseem-sip.xml taken from
https://github.com/saghul/sipp-scenarios/blob/master/
        sipp_uas_200_multiple_streams.xml
Run
./sipp -sd uas to get all the Server scenarios
'''
import logging, re
import socket, select
import sys, threading, time
import select, random
import cmd
import platform

socketInputs = []
socketClient = {}
class Connect():
  def __init__(self, server):
    self.sipServer = server
    self.address = (server, 5060)
    try:
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
      print 'Failed to create socket'
      sys.exit()
  def send(self, data):
    self.sock.sendto(data, self.address)
  def recv123(self, size):
    dataR, serverR = self.sock.recvfrom(512)
    return dataR,serverR

class Client():
  def __init__(self, params):
    global socketInputs
    global socketClient
    self.conn = Connect(params['server'])
    self.conn.client = self
    self.params = params
    self.calling = params["calling"]
    
    # From the Address in resource.txt ignore the Display Name
    tmp = re.split(r'[ ]', self.calling)[1]
    # Remove the <>
    self.callingAddress = re.sub('[<>]', '', tmp)
    # Remove the sip:
    self.callingAddress = self.callingAddress.replace("sip:", '')
    # Done
    
    print self.callingAddress
    self.called = params["called"]
    self.seq = 1 # Initialize the counter for this client
    self.CallID = 400000+random.randint(0,500000)
    self.FSM=FSM(self)
    socketInputs.append(self.conn.sock)
    # Keep a dict of {sock:client} for easy lookup of client after select()
    socketClient[self.conn.sock] = self
    
def sipParser(client, data):
  # Get the Message Start Line
  splitdata = data.split("\n")
  if "OK" in splitdata[0]:
    logging.debug(splitdata[0])
    client.FSM.run("OK")
  elif "RINGING" in splitdata[0]:
    logging.debug(splitdata[0])
    client.FSM.run("RINGING")
  else:
    print "Other Message"
  # Now, get the Headers, skip the 1st Start line
  for line in splitdata[1:]:
    for word in line.split(" "):
      if word == "CSeq:":
        logging.debug("CSeq:", line)
        break
      if word == "To:":
        logging.debug("To:", line)
        break
      elif word == "From:":
        logging.debug("From:", line)
        break
      elif word == "Contact:":
        logging.debug("Contact:", line)
        break
      elif word == "Call-ID:":
        logging.debug("Contact:", line)
        break
      elif word == "Content-Length:":
        logging.debug("Content-Length:", line)
        break
      elif word == "Content-Type:":
        logging.debug("Content-Length:", line)
        break
      elif word == "" or word == "\r":
        break
      else:
        # Check for Media Parameters
        for letters in word.split("="):
          if letters in ['v','o','s','c','t','m','a']:
            logging.debug("Media:", letters, "in", line)
            break    

def recvThread(conn):
  global socketClient
  logging.warn('Recv Thread')
  while True:
    readable, writable, exceptional = \
                        select.select(socketInputs, [], [])
    for s in readable:
      data = s.recv(1024)
      # retrive the client pointer from sock looking up the Dict
      sipParser(socketClient[s], data)
  
  while True:
    try:
      data, server = conn.sock.recvfrom(512)
      sipParser(conn, data)
    except Exception, e:
      print("Something's wrong with %s. Exception type is %s" % (conn, e))

'''
To, From, CSeq, Call-ID, Max-Forwards, Via are mandatory in all SIP requests.
'''
def addMandatoryHdrs(client, type):
  # "To:" is filled up by the called of this function
  # If a request contained a To tag in the request, the To header field
  # in the response MUST equal that of the request. The UAS MUST add a
  # tag to the To header field in the response, if it was missing in request.
  
  # The VIA with the Branch param is mandatory. Part after MAGIC cookie z9hG4bK
  # could be the hash ID of the transaction.
  # Via contains the address at which caller is expecting to receive
  # responses to this request.
  # TBD: Put the digits following the cookie in the Client struct, i.e. 11111
  Via = 'Via: SIP/2.0/UDP ' + client.callingAddress + ' ;branch=z9hG4bK-11111\r\n'
  # The From field MUST contain a new "tag" parameter, chosen by the UAC.
  From = 'From: ' + str(client.calling) + '; tag=call1\r\n'
  # CSeq increments for every request from client (Except ACK, CANCEL)
  # For new requests, registger and Bye - cseq is incremented
  CSeq = 'CSeq: ' + str(client.seq) + ' ' + type +'\r\n'
  if type != "ACK":
    client.seq = client.seq+1
  else:
    print "ACK: Not incrementing CSeq"
  # The Call-ID is a unique identifier to group together messages.
  # It MUST be the same for all requests and responses sent by either UA
  # in a dialog.  It SHOULD be the same in each registration from a UA.
  # TBD - same the CallID to be used for periodic registration.
  CallID = 'Call-ID: ' + str(client.CallID) + '\r\n'
  # If  Max-Forwards value reaches 0 before the request reaches its
  # destination, it will be rejected with a 483(Too Many Hops) error response.
  MF = 'Max-Forwards: 70\r\n'
  client.pkt = Via + CSeq + From + CallID + MF

def sendRegister(client, event):
# Mandatory request line contains  Method, Request-URI, and SIP version.
  Start = 'REGISTER sip:'+client.conn.sipServer+' SIP/2.0\r\n'
  To = 'To: ' + str(client.calling) + '\r\n'
  Allow = 'Allow: INVITE,ACK,OPTIONS,BYE,CANCEL,SUBSCRIBE,NOTIFY,REFER,'+\
          'MESSAGE,INFO,PING\r\n'
  addMandatoryHdrs(client, 'REGISTER')
  client.pkt = Start + To + client.pkt + Allow + '\r\n'
  client.conn.send(client.pkt)
  return "OK"

def registerOK(client, event):
  logging.warn("Register OK recvd for client %s", client.params['calling'])
  sendInvite(client)
  return "OK"

def inviteResp(client, event):
  if event == "RINGING":
    logging.warn("RINGING recvd. for client %s", client.params['calling'])
    return "NO-STATE-CHANGE"
  elif event == "OK":
    logging.warn("Invite OK recvd for client %s", client.params['calling'])
    sendAck(client)
    return "OK"

# Add SDP params. No space between name=value pair
def addSDP(client):
  # Add SDP session level params
  sdp = "v=0\r\n"
  #    o=<user> <sess-id> <sess-ver> <nettype> <addrtype> <unicast-addr>
  sdp =  sdp + "o=user1 1234567 1234567 IN IP4 1.1.1.1\r\n"
  sdp =  sdp + "s=Audio Session\r\n"
  #    c=<nettype> <addrtype> <connection-address>
  #    This is the IP for bearer session
  sdp =  sdp + "c=IN IP4 1.1.1.1\r\n"
  # Add SDP time level params
  sdp =  sdp + "t=0 0\r\n"
  # Add SDP media level params
  #    m=<media> <port> <proto> <fmt> ...
  sdp =  sdp + "m=audio 6000 RTP/AVP 0\r\n"
  sdp =  sdp + "a=rtpmap:0 PCMU/8000\r\n"
  sdp =  sdp + "a=sendrecv\r\n"
  sdp =  sdp + "m=video 6001 RTP/AVP 34\r\n"
  sdp =  sdp + "a=rtpmap:34 h263/90000\r\n"
  sdp =  sdp + "a=fmtp:34 QCIF=2\r\n"
  sdp =  sdp + "a=sendrecv\r\n"
  return sdp

def sendInvite(client):
  logging.debug("Send Invite")
  Start = 'INVITE '+client.params['calledUri']+' SIP/2.0\r\n'
  # To has logical recipient of the request. Allows for Display Name
  To = 'To: ' + str(client.called) + '\r\n'
  addMandatoryHdrs(client, 'INVITE')
  cl = "Content-Length: 200\r\n"
  ct = "Content-Type: application/sdp\r\n"
  # An additional CRLF is inserted between Message Line and Body
  client.pkt = Start + To + client.pkt + cl + ct + '\r\n'
  sdp = addSDP(client)
  client.pkt = client.pkt + sdp
  client.conn.send(client.pkt)
  return "INVITE-SENT"

def sendAck(client):
  logging.debug("Send Ack")
  Start = 'ACK '+client.params['calledUri']+' SIP/2.0\r\n'
  # To has logical recipient of the request. Allows for Display Name
  To = 'To: ' + str(client.called) + '\r\n'
  addMandatoryHdrs(client, 'ACK')
  cl = "Content-Length: 200\r\n"
  client.pkt = Start + To + client.pkt + cl
  client.conn.send(client.pkt)
  return "ACK-SENT"

def callSetUp(client, event):
  print "FSM Finish"

class FSM:
  #Use List for FSM
  states = ['START', 'REG-SENT', 'INV-SENT', 'INV-OK', 'FINISH']
  fsm = [
  {'ST':'START',    'EV':'ANY', 'NEXT':'REG-SENT', 'FUNC':sendRegister},
  {'ST':'REG-SENT', 'EV':'ANY', 'NEXT':'INV-SENT',  'FUNC':registerOK},
  {'ST':'INV-SENT', 'EV':'ANY', 'NEXT':'INV-OK',   'FUNC':inviteResp},
  {'ST':'INV-OK',   'EV':'ANY', 'NEXT':'FINISH',   'FUNC':callSetUp}
  ]
  def __init__(self, client):
    logging.debug("New FSM init")
    self.client = client
    self.FSM = self.fsm
    self.startState = 'START'
    self.state = "START"
  def run(self, event):
    #print "FSM: Current State:", \
    #  self.fsm[self.states.index(self.state)], " Event:", event
    handler = self.fsm[self.states.index(self.state)]['FUNC']
    status = handler(self.client, event)
    if status == "OK":
      self.state = self.fsm[self.states.index(self.state)]['NEXT']
      logging.warn(self.state)

def sipStart(params):
  conn = None
  logging.warn("\nSIPStart: %s", params["calling"])
  client = Client(params)
  # send a pkt so that sock is valid, and recv in recvThread
  # does not give an error. Socket doesn't have an address untill its
  # either binded or data is sent.
  client.conn.send(".")
  recvT = threading.Thread(target=recvThread,
                                      args=(client.conn,))
  recvT.start()
  # recvThread.join() - not needed since main() waits for threads to
  # complete.
  client.FSM.run("START")

'''
Set some default values for params coming from resource.txt file
Syntax: name=value1 value2
clients[]] is an array of Dict items of all params for a particular client.
e.g.: Clients:
[{'calling': '"Aseem" <sip:aseem@yahoo.com>', 'Client': '',
   'called': '"Kavita" <sip:kavita@ymail.com>', 'server': '172.17.19.222'
 },
 {'calling': '"Dhruv" <sip:dhruv@yahoo.com>', 'Client': '',
  'called': '"Pallavi" <sip:pallavi@ymail.com>', 'server': '172.17.19.222'
 }
]
'''
def loadParams():
  params = {}
  clients = []
  with open("resource.txt", "r") as f:
    for line in f:
      nameValue = re.split(r'[=, \r\n]', line)
      name = nameValue[0]
      if re.search('^#', name):
        continue   # Ignore lines starting with #
      if name == "Client":
        params = {}
        clients.append(params)
      value = nameValue[1]
      for i in range(2, len(nameValue)):
        value = value + ((" " + nameValue[i]) if nameValue[i] else '')
      params[name] = value
  logging.warn("\nClients: %s", clients)
  return clients

class CmdLine(cmd.Cmd):
  def do_greet(self, line):
    print "hello", line
  def do_EOF(self, line):
    return True

def cmdThread(param):
  #Ctrl-D to drop out of the interpreter
  prompt = CmdLine()
  prompt.prompt = '> '
  prompt.cmdloop()

if __name__ == '__main__':
  #logging.basicConfig(format='%(asctime)s (%(threadName)s):
  # %(message)s', level=logging.WARN)
  logging.basicConfig(format='(%(threadName)s): %(message)s', level=logging.WARN)
  clients = loadParams()
  for x in range(len(clients)):
    sipStart(clients[x])
  if platform.system() == 'Linux':
    print platform.system()
    cmdT = threading.Thread(target=cmdThread, args=("CMD",))
    cmdT.start()
  else:
    # Some issue with select.select() call in windows. TBD - work on this.
    print platform.system()



