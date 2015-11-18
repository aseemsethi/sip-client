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
  def recv(self, size):
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
    print splitdata[0]
    client.FSM.run("OK")
  elif "RINGING" in splitdata[0]:
    print splitdata[0]
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
        logging.debug("CSeq:", line)
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
            print "Media:", letters, "in", line
            break
      

def recvThread(conn):
  global socketClient
  logging.debug('Recv Thread')
  while True:
    readable, writable, exceptional = \
                        select.select(socketInputs, [], [])
    for s in readable:
      data = s.recv(512)
      # retrive the client pointer from sock looking up the Dict
      sipParser(socketClient[s], data)
  
  while True:
    try:
      #data, server = conn.recv(1024)
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
  # could be the hash ID of the transaction
  # TBD: Put the digits following the cookie in the Client struct, i.e. 11111
  Via = 'Via: SIP/2.0/UDP yahoo.com ;branch=z9hG4bK-11111\r\n'
  # The From field MUST contain a new "tag" parameter, chosen by the UAC.
  From = 'From: ' + str(client.calling) + '; tag=call1\r\n'
  # CSeq increments for every request from client (Except ACK, CANCEL)
  # For new requests, registger and Bye - cseq is incremented
  CSeq = 'CSeq: ' + str(client.seq) + ' ' + type +'\r\n'
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
  print "Send Register"
# Mandatory request line contains  Method, Request-URI, and SIP version.
  Start = 'REGISTER sip:'+client.conn.sipServer+' SIP/2.0\r\n'
  To = 'To: ' + str(client.calling) + '\r\n'
  Allow = 'Allow: INVITE,ACK,OPTIONS,BYE,CANCEL,SUBSCRIBE,NOTIFY,REFER,'+\
          'MESSAGE,INFO,PING'
  addMandatoryHdrs(client, 'REGISTER')
  client.pkt = Start + To + client.pkt + Allow
  client.conn.send(client.pkt)
  return "OK"

def registerOK(client, event):
  print "Register OK recvd"
  sendInvite(client)
  return "OK"

def inviteResp(client, event):
  if event == "RINGING":
    print "RINGING recvd."
    return "NO-STATE-CHANGE"
  elif event == "OK":
    print "Invite OK recvd"
    return "OK"

def addSDP(client):
  # Add SDP message
  sdp = "v=0\r\n"
  sdp =  sdp + "o=user1 53655765 2353687637 IN IP6 [::1]\r\n"
  sdp =  sdp + "s=-\r\n"
  sdp =  sdp + "c=IN IP6 ::1\r\n"
  sdp =  sdp + "t=0 0\r\n"
  sdp =  sdp + "m=audio 6000 RTP/AVP 0\r\n"
  sdp =  sdp + "a=rtpmap:0 PCMU/8000\r\n"
  sdp =  sdp + "a=sendrecv\r\n"
  sdp =  sdp + "m=video 6001 RTP/AVP 34\r\n"

  sdp =  sdp + "a=rtpmap:34 h263/90000\r\n"
  sdp =  sdp + "a=fmtp:34 QCIF=2\r\n"
  sdp =  sdp + "a=sendrecv\r\n"
  client.pkt = client.pkt + sdp

def sendInvite(client):
  print "Send Invite"
  Start = 'INVITE sip:'+str(client.called)+' SIP/2.0\r\n'
  # To has logical recipient of the request. Allows for Display Name
  To = 'To: ' + str(client.called) + '\r\n'
  addMandatoryHdrs(client, 'INVITE')
  cl = "Content-Length: 200\r\n"
  ct = "Content-Type: application/sdp\r\n"
  client.pkt = Start + To + client.pkt + cl + ct
  addSDP(client)
  client.conn.send(client.pkt)
  return "INVITE-SENT"
  
def callSetUp(client, event):
  print "FSM Finish"

class FSM:
  #Use List for FSM
  states = ['START', 'REG-SENT', 'INV-SENT', 'INV-OK', 'FINISH']
  fsm = [
  {'ST':'START',    'EV':'ANY', 'NEXT':'REG-SENT', 'FUNC':sendRegister},
  {'ST':'REG-SENT', 'EV':'ANY', 'NEXT':'INV-SENT',  'FUNC':registerOK},
  {'ST':'INV-SENT', 'EV':'ANY', 'NEXT':'INV-OK',   'FUNC':inviteResp},
  {'ST':'INV-OK',   'EV':'ANY', 'NEXT':'FINISH',   'FUNC':callSetUp},
  {'ST':'FINISH',   'EV':'ANY', 'NEXT':'FINISH',   'FUNC':callSetUp}
  ]
  def __init__(self, client):
    print "New FSM init"
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
      print self.state

def sipStart(params):
  conn = None
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
'''
def loadParams():
  params = {}
  sipServer = '192.168.2.7'
  # Address: "Display Name" + <SIP URI>
  calling = 'ABC' + ' ' + '<sip:abc@yahoo.com>'  
  called  = 'DEF' + ' ' + '<sip:def@yahoo.com>'  # of type Address
  with open("resource.txt", "r") as f:
    for line in f:
      nameValue = re.split(r'[=, \r\n]', line)
      name = nameValue[0]
      if name == "#": continue   # Ignore lines starting with #
      value = nameValue[1]
      for i in range(2, len(nameValue)):
        value = value + ((" " + nameValue[i]) if nameValue[i] else '')
      params[name] = value
  return params

if __name__ == '__main__':
  logging.basicConfig(format='%(asctime)s (%(threadName)-10s) \
              %(message)s', level=logging.WARN)
  params = loadParams()
  print params
  sipStart(params)
