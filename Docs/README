'''
Run the SIP Server - sipp as
./sipp -sf aseem-sipp.xml -trace_logs -trace_msg

Run
./sipp -sd uas to get all the Server scenarios

aseem-sipp.xml is a simple xml file as follows:
<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">
<scenario name="Basic Test">
  <recv request="REGISTER" crlf="true">
  </recv>
  <send>
    <![CDATA[
      SIP/2.0 200 OK
      [last_CSeq:]
      [last_Call-ID:]
      [last_From:]
      Contact:<sip:192.168.1.112>
      Content-Length: 0
    ]]>
  </send>
</scenario>

Message Format
==============
generic-message  =  start-line
                    *message-header
                    CRLF
                    [ message-body ]
start-line       =  Request-Line / Status-Line

REGISTER sip:10.10.1.99 SIP/2.0
CSeq: 1 REGISTER
Via: SIP/2.0/UDP 10.10.1.13:5060;
  branch=z9hG4bK78946131-99e1-de11-8845-080027608325;rport
User-Agent: Ekiga/3.2.5
From: <sip:13@10.10.1.99>
  ;tag=d60e6131-99e1-de11-8845-080027608325
Call-ID: e4ec6031-99e1-de11-8845-080027608325@vvt-laptop
To: <sip:13@10.10.1.99>
Contact: <sip:13@10.10.1.13>;q=1
Allow: INVITE,ACK,OPTIONS,BYE,CANCEL,SUBSCRIBE,NOTIFY,REFER,MESSAGE,
  INFO,PING


Invite Msg
INVITE sip:41215500309@192.168.1.15 SIP/2.0
Via: SIP/2.0/UDP 192.168.1.9;branch=z9hG4bKfae8cb69f547b8cb
Max-Forwards: 70
To: <sip:41215500309@192.168.1.15>
From: <sip:41215500311@192.168.1.15>;tag=102
User-Agent: UDP Packet Sender
Call-ID: 070403-200101@192.168.1.9
CSeq: 5000 INVITE
Contact: <sip:41215500311@192.168.1.9>
Content-Type: application/sdp
Content-Length: 0


Expires: 3600
Content-Length: 0
Max-Forwards: 70


Cancel
CANCEL sip:41215500309@192.168.1.15 SIP/2.0
Via: SIP/2.0/UDP 192.168.1.9;branch=z9hG4bKfae8cb69f547b8cb
Max-Forwards: 70
To: <sip:41215500309@192.168.1.15>
From: <sip:41215500311@192.168.1.15>;tag=102
User-Agent: UDP Packet Sender
Call-ID: 070403-200101@192.168.1.9
CSeq: 5000 CANCEL
Contact: <sip:41215500311@192.168.1.9>
Content-Type: application/sdp
Content-Length: 0
'''
