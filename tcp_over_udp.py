import socket, time
import threading
import sys, select
import hashlib

global flag_bye , flag_con #flag_bye - stop the entire program/ flag_con has different meanings
global socketClient, socketServer
global change_j, go #variable go "stops" main thread if the timer is out 
                    #change_j - is used not to stop the server if one/two fragment didn't come, so it can count three new fragments from begining
go = 0

ServerIP = input("ServerIP: ")
clientIP = input("ClientIP: ")
port = 9090
MAX_fragmentSize  = 1500


def outoftime_server(address): #server:  (if client hasn't sent anything for a long time server send a question: "brake connection?")
    print("server timer is out")
    global flag_con 
    global flag_bye, go 
    global socketServer
    x = thingToSend("00004", 12, 0, 1, "", 1 )
    socketServer.sendto(x, address)
    print("Sending whether to stay in connection")
    msg1 = socketServer.recvfrom(MAX_fragmentSize) 
    msg = msg1[0]
    if(msg[0:5].decode()=="00005"): #further things server do depending on the answear 
        if(msg[12:int.from_bytes(msg[5:7], byteorder="big")].decode()=="No"):
            print("Server: break connection")
            flag_bye = 1
            flag_con = 2
        elif(msg[12:int.from_bytes(msg[5:7], byteorder="big")].decode()=="Yes"):
            print("Server: stay in connection")
            flag_con =1
        elif(msg[12:int.from_bytes(msg[5:7], byteorder="big")].decode()=="Change mode"):
            print("Server: gonna be a client now")
            flag_con=2
    go = 1
   
def mytimer_connect_server(address):  #keep-alive timer for server
    global connection_timer_ser
    connection_timer_ser = threading.Timer(30.0, outoftime_server, args=[address])    

def outoftime_client( addServer): #client: to brake/not to brake
    print("client is out of time")
    global flag_bye
    global flag_con, go
    global socketClient
    msg1 = socketClient.recvfrom(MAX_fragmentSize)
    msg = msg1[0]
    print("Got question: whether to stay in connection.")
    if(msg[0:5].decode()=="00004"): #client have to decide whether he/she wants to stay in connection further
        print("Stay in connection? (Yes/No/Change mode) ")
    go = 1
    
def mytimer_connect_client(addServer):   #keep-alive timer for client
    global connection_timer_clt
    connection_timer_clt = threading.Timer(30.0, outoftime_client, args=[addServer])    

def send_request(request_numbers, address): #utility function which sends a string of ordinal numbers of requested fragments
    global socketServer
    request_numbers =  request_numbers[:-1]
    x = thingToSend("00003", len(request_numbers)+12, 0, 1, request_numbers, 1)
    socketServer.sendto(x, address)
    return "" 

def no_fragment(gotten_numbers, j, last_come, address, amount):
    request_numbers = ""
    print("Fragment/s didnt came or ACK wasn't delivered")
    print(last_come)
    kakak=0
    while(kakak<last_come + j - int(j/3)*3  and kakak<amount):
        print(kakak)
        if(gotten_numbers[kakak]==False): #forming a string of ordinal numbers of requested fragments
            request_numbers += str(kakak)+"+"
            print("Requested: " + str(kakak))
        kakak+=1
    if(request_numbers!=""): #if not all 3 fragments came
        print("Requested numbers: " + request_numbers)
        send_request(request_numbers, address)
    else: #if ACK was not sent before
        print("That was only ACK!")
        ACK=str.encode("00000")
        socketServer.sendto(ACK, address)
    global change_j
    change_j = 1
    
def mytimer_frag(gotten_numbers, j, last_come, adress, amount):  #timer: fragment didn't come or ACK wasn't delivered
    global receiving_timer
    receiving_timer = threading.Timer(3.0, no_fragment, args=[gotten_numbers, j, last_come, adress, amount])   

def md5(f): #smth like checksum just for bytes in the file
    result = hashlib.md5()
    for chunk in range(0, len(f), 128):
        result.update(f[chunk:chunk+128])
    return result.hexdigest()

def calc_checksum(string): #checksum
    sum = 0
    for i in range(len(string)):
        sum = sum + ord(string[i])
    temp = sum % 256 
    rem = -temp  
    return '%2X' % (rem & 0xFF)

def thingToSend(typeOfThing, length, ordinalNumber, checkSum, data, Encode): #utility function which is used to send almost all types of objects
    typeOfThing = str.encode(typeOfThing)  
    if(checkSum==1):
        checkSum = (calc_checksum(data)).encode()
    else:
        checkSum=(calc_checksum(md5(data))).encode() # if it is a file data is already byte type, so i use a utility function md5(bytes) and then checksum
    if(ordinalNumber == 2):
        make = input("Make a mistake? (Y/N)")
        if (make=="Y"):
            data = make_mistake(data, Encode)
    length = length.to_bytes(2, byteorder="big")
    if(Encode==1):
        data = str.encode(data)
    ordinalNumber = ordinalNumber.to_bytes(3, byteorder="big")
    x = typeOfThing + length + ordinalNumber + checkSum + data
    return x
     
def make_mistake(data, type):
    if(type == 1): #message
        data =data[:1]+ "0" + data[2:]
    else:
        data = data[:1] + (3).to_bytes(3, byteorder = "big") +data[4:]
    return data
    


while(True): 
    status = input("Choose you mode (server/client): ")

    if(status=="client"): #as a client

        addServer  = (ServerIP, port) #server address
        socketClient = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) 
        x = str.encode("00001") #i want to send smth now
        socketClient.sendto(x, addServer) 
        ackCon = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
        AckConn = ackCon[0]
        if((AckConn[0:5]).decode()=="00000"): #if all 3 fragments were delivered right
            print("ACK for the connection: good")
        fragmentSize = 0 

        while(True):
            
            flag_con = 0 #these are expleined at the top
            flag_bye = 0
            while(True): #reading size of a fragment from consol
                fragmentSize =  int(input("Enter max size of fragment: "))
                if(fragmentSize>MAX_fragmentSize-20-8-12):   #max - ip_head - udp_head - my_head  
                    print("Error: too big data, Max: " + MAX_fragmentSize-20-8-12)
                else: 
                    break
            mytimer_connect_client(addServer)
            connection_timer_clt.start() 
            print("Enter type of data (message/.pdf/.txt/....): ") #reading the type of the "thing" ehich will be sent
            type_of_data = input()
            if(type_of_data == "No"):
                x = thingToSend("00005", 14, 0, 1, "No", 1)
                socketClient.sendto(x, addServer)
                print("Client: break connection")
                flag_bye=1
                flag_con=2
            elif (type_of_data == "Yes" ):
                x = thingToSend("00005", 15, 0, 1, "Yes", 1)
                socketClient.sendto(x, addServer)
                print("Client: stay in connection")
                flag_con = 1
            elif (type_of_data == "Change mode"):
                x = thingToSend("00005", 23, 0, 1, "Change mode", 1)
                socketClient.sendto(x, addServer)
                flag_con =2
                print("Client: want to be server now")
            
            if(flag_con==2):
                break
            elif (flag_con==1):
                continue
            
            
            if (type_of_data=="message"): #if it is just a message

                msgClient = input("Enter your message: ")
                new_msg =  range(0, len(msgClient), fragmentSize) #dividing the message into segments
                x = thingToSend("00002", fragmentSize, len(new_msg), 1, "00006", 1) #notice to server which contains: the max size of fragment, which will be sent soon, 
                                                                                    #amount of fragments and also the notice that it is a message (not a .pdf or .png ...)
                
                socketClient.sendto(x, addServer) 
                connection_timer_clt.cancel() #cancel timer if we send smth
                ackCon = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                AckConn = ackCon[0]
                if((AckConn[0:5]).decode()=="00000"): #if all 3 fragments were delivered right
                    print("ACK for amount of fragments: good")
                
                j = 0 #counting the amout of sent fragments (to send 3 of them and then wait for the ACK)
                for mes_frag in new_msg:
                    x = thingToSend("00006", len(msgClient[mes_frag:(mes_frag+fragmentSize)])+12, int(mes_frag/fragmentSize), 1, msgClient[mes_frag:(mes_frag+len(msgClient[mes_frag:(mes_frag+fragmentSize)]))], 1)      #fragment + head
                    socketClient.sendto(x, addServer)
                    print(int(mes_frag/fragmentSize))

                    j+=1
                    if((j % 3==0) & (j!=0)): #if we have sent 3 fragments we are waiting for ACK 

                        msgServer1 = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                        msgServer = msgServer1[0]
                        if((msgServer[0:5]).decode()=="00000"): #if all 3 fragments were delivered right
                            print("ACK: good")

                        elif ((msgServer[0:5]).decode()=="00003"): #if not, then we have a string(request) which contains ordinal number of not delivered fragments
                            print("Smth didn't come, so i'm going to send it again")
                            llll=int.from_bytes(msgServer[5:7], byteorder="big")-12 
                            check_sum2=msgServer[10:12].decode()
                            check_sum3=calc_checksum((msgServer[12:12+llll]).decode())
                            if(check_sum2==check_sum3):
                                request_num = (msgServer[12:12+llll].decode()).split("+")
                                k=0
                                while (k<len(request_num)): #sending requested by server fragments
                                    order = int(request_num[k])
                                    len_mes_frag = len(msgClient[(order*fragmentSize):(order*fragmentSize+fragmentSize)])+12
                                    mes_frag_data = msgClient[(order*fragmentSize):(order*fragmentSize+fragmentSize)]
                                    x = thingToSend("00006", len_mes_frag, order, 1, mes_frag_data, 1)
                                    socketClient.sendto(x, addServer)
                                    j+=1
                                    k+=1
                            

                msgServer1 = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                msgServer = msgServer1[0]
                while(True):
                    if((msgServer[0:5]).decode()=="00000"): #if all fragments were delivered right
                        print("ACK for all message: good")
                        break
                    elif ((msgServer[0:5]).decode()=="00003"): #if not, then we have a string(request) which contains ordinal number of not delivered fragments
                        print("Smth didn't come, so i'm going to send it again")
                        llll=int.from_bytes(msgServer[5:7], byteorder="big")-12 
                        check_sum2=msgServer[10:12].decode()
                        check_sum3=calc_checksum((msgServer[12:12+llll]).decode())
                        if(check_sum2==check_sum3):
                            request_num = (msgServer[12:12+llll].decode()).split("+")
                            k=0
                            while (k<len(request_num)): #sending requested by server fragments
                                order = int(request_num[k])
                                len_mes_frag = len(msgClient[(order*fragmentSize):(order*fragmentSize+fragmentSize)])+12
                                mes_frag_data = msgClient[(order*fragmentSize):(order*fragmentSize+fragmentSize)]
                                x = thingToSend("00006", len_mes_frag, order, 1, mes_frag_data, 1)
                                socketClient.sendto(x, addServer)
                                j+=1
                                k+=1

            else: # if it is a file
                # print("Enter path to your file (Desktop/file): ") #asking for the path to the file, without its type: "Desktop/title" , not "Desktop/title.png"
                filename = input("Enter path to your file (Desktop/file): ")
                fileBytes = open(filename+type_of_data, "rb").read()  #reading the file like bytes
                new_msg =  range(0, len(fileBytes), fragmentSize) # dividing into fragments
                x = thingToSend("00002", fragmentSize, len(new_msg), 1, type_of_data, 1) # notice for the server, which contains: the max size of fragment, which will be sent soon, 
                                                                                        #amount of fragments and also the notice whst type of file it is going to be(".png" or ".pdf" or ".txt")
                print("Amount of fragments: "+ str(len(new_msg)))
                socketClient.sendto(x, addServer)
                connection_timer_clt.cancel()
                ackCon = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                AckConn = ackCon[0]
                if((AckConn[0:5]).decode()=="00000"): #if all 3 fragments were delivered right
                    print("ACK for amount of fragments: good")
                while(len(type_of_data)!=5):
                    type_of_data=" "+type_of_data
                j = 0 
                for file_frag in new_msg:
                    len_of_frag = len(fileBytes[file_frag:(file_frag+fragmentSize)])+12
                    num = int(file_frag/fragmentSize)
                    dat = fileBytes[file_frag:(file_frag+len_of_frag-12)]
                    x = thingToSend(type_of_data, len_of_frag, num, 0, dat, 0)    #fragment+head  
                    socketClient.sendto(x, addServer)
                    print(num)
                    j+=1

                    if(((j % 3==0) & (j!=0)) or (num == len(new_msg)-1)):  #if we have sent 3 fragments we are waiting for ACK 
    
                        msgServer1 = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                        msgServer = msgServer1[0]
                        if((msgServer[0:5]).decode()=="00000"): #if all fragments were delivered right
                            print("ACK : good")
                        elif ((msgServer[0:5]).decode()=="00003"):
                            print("Something didn't come, so i'm going to send it again")
                            llll=int.from_bytes(msgServer[5:7], byteorder="big")-12
                            check_sum2=msgServer[10:12].decode()
                            check_sum3=calc_checksum((msgServer[12:12+llll]).decode())
                            if(check_sum2==check_sum3):
                                print("A request has come: " + msgServer[12:12+llll].decode())
                                request_num = (msgServer[12:12+llll].decode()).split("+")
                                k=0
                                while (k<len(request_num)):
                                    order = int(request_num[k])
                                    len_file_frag = len(fileBytes[(order*fragmentSize):(order*fragmentSize+fragmentSize)])+12
                                    data_file_frag = fileBytes[(order*fragmentSize):(order*fragmentSize+fragmentSize)]
                                    x = thingToSend(type_of_data, len_file_frag, order, 0, data_file_frag, 0)
                                    socketClient.sendto(x, addServer)
                                    j+=1
                                    k+=1

                            time.sleep(3) 
                while(True): 
                    msgServer1 = socketClient.recvfrom(MAX_fragmentSize) #recieving answer from server
                    msgServer = msgServer1[0]
                    if((msgServer[0:5]).decode()=="00000"): #if all fragments were delivered right
                        llll=int.from_bytes(msgServer[5:7], byteorder="big")-12
                        check_sum2=msgServer[10:12].decode()
                        check_sum3=calc_checksum((msgServer[12:12+llll]).decode())
                        if(check_sum2==check_sum3):
                            print("ACK for the whole file: good")
                            file_path = msgServer[12:12+llll].decode()
                            print("Path: " + file_path)
                            break
                    elif ((msgServer[0:5]).decode()=="00003"):
                        print("Something didn't come, so i'm going to send it again")
                        llll=int.from_bytes(msgServer[5:7], byteorder="big")-12
                        check_sum2=msgServer[10:12].decode()
                        check_sum3=calc_checksum((msgServer[12:12+llll]).decode())
                        if(check_sum2==check_sum3):
                            print("A request has come: " + msgServer[12:12+llll].decode())
                            request_num = (msgServer[12:12+llll].decode()).split("+")
                            k=0
                            while (k<len(request_num)):
                                order = int(request_num[k])
                                len_file_frag = len(fileBytes[(order*fragmentSize):(order*fragmentSize+fragmentSize)])+12
                                data_file_frag = fileBytes[(order*fragmentSize):(order*fragmentSize+fragmentSize)]
                                x = thingToSend(type_of_data, len_file_frag, order, 0, data_file_frag, 0)
                                socketClient.sendto(x, addServer)
                                j+=1
                                k+=1
            
            # mytimer_connect_client(addServer)
            # connection_timer_clt.start() 
            if(flag_con==2):
                connection_timer_clt.cancel() 
                break
            elif (flag_con==1):
                continue

        if( flag_bye==1):
            socketClient.close()
            break
        else:
            socketClient.close()
            pom = ServerIP
            ServerIP = clientIP
            ClientIP = pom

        
    elif (status=="server"): #as a server
        global change_j
        change_j = 0
        socketServer = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)  # Create a socket
        socketServer.bind((ServerIP, port))   # Bind to address and ip
        bytesAddressPair = socketServer.recvfrom(MAX_fragmentSize) #receiving first thing from client
        
        
        first = bytesAddressPair[0]
        address = bytesAddressPair[1] #remembering address of client
        print("Sending ACK for the connection")
        ACK=str.encode("00000")
        socketServer.sendto(ACK, address)
        
        while(True):
            mytimer_connect_server(address)
            connection_timer_ser.start() 
            flag_con = 0
            flag_bye = 0
            go = 0
            while(True):
                okh, o, e = select.select([socketServer], [], [], 33)
                if (okh):
                    data = socketServer.recvfrom(MAX_fragmentSize)
                    bytesAddressPair =data
                    connection_timer_ser.cancel() #cancel timer if we receive smth
                    ACK=str.encode("00000")
                    socketServer.sendto(ACK, address)
                    first = bytesAddressPair[0]
                    break
                else:
                    while(go != 1):
                        a = 0
                    break
            if(flag_con == 1):
                continue
            elif (flag_con==2):
                break

            if(((first[0:5]).decode())=="00002"):  #the first thing client send must be a notice about next file/message
               
                number_of_fragments_receive = int.from_bytes(first[7:10], byteorder="big") #founding out how many fragments we have to receive
                print("Number of ragments to receive:" + str( number_of_fragments_receive ))  
                number_of_fragments_come=0
                fragmentSize= int.from_bytes(first[5:7], byteorder="big") #founding out the max size of a fragment
                print("The max size of a fragment client is going to send: " + str(fragmentSize) )
                type_next = (first[12:17]).decode() #founding out the type of data client will send: message/.png/.pdf/.txt/.py...
                gotten_numbers= [False] * number_of_fragments_receive #this string will contain an ordinal numbers of fragments which came
                last_come = 0 
                j = 0
                change_j = 0
                
                if(type_next=="00006"): #if it is a message
                    mytimer_frag(gotten_numbers, j, last_come, address, number_of_fragments_receive)
                    receiving_timer.start() 
                    msg = [] #the text of a message
                    
                    while(number_of_fragments_come!=number_of_fragments_receive): #while we don't have all the fragments
                        if(change_j == 1):
                            j = round(j/3)*3
                            change_j= 0
                        else: j+=1

                        msg_fragment1 = socketServer.recvfrom(MAX_fragmentSize)
                        receiving_timer.cancel() 
                        msg_fragment = msg_fragment1[0]
                        llll=int.from_bytes(msg_fragment[5:7], byteorder="big")-12
                        check_sum2=msg_fragment[10:12].decode()
                        check_sum3 = calc_checksum((msg_fragment[12:12+llll]).decode())
                        if(check_sum2==check_sum3):  #if checksums are equal, which means data of a fragment was not changed while delivering
                            in_order = int.from_bytes((msg_fragment[7:10]), byteorder="big") #founding out the ordinal number of a fragment
                            msg.insert(in_order, (msg_fragment[12:12+llll]).decode()) #placing part of a message to its place
                            print(in_order)
                            gotten_numbers[in_order]=True
                            number_of_fragments_come+=1
                            

                            if(in_order>last_come):
                                last_come=in_order
                        if(((j % 3 == 0) & (j!=0)) or (number_of_fragments_come==number_of_fragments_receive)): #after receiving 3 fragments
                            print("Checking after 3")
                            request_numbers = ""
                            kakak = 0
                            while(kakak<last_come):
                                if(gotten_numbers[kakak]==False):
                                    request_numbers += str(kakak)+"+"
                                    print("Requested: " + str(kakak))
                                kakak+=1
                            if(request_numbers!=""): #if not all 3 fragments came
                                print("Requested numbers: " + request_numbers)
                                send_request(request_numbers, address)
                                time.sleep(3) 
                            else: #if all 3 fragments came
                                print("I just going to send ACK")
                                ACK=str.encode("00000")
                                socketServer.sendto(ACK, address)
                        mytimer_frag(gotten_numbers, j, last_come, address, number_of_fragments_receive)
                        receiving_timer.start() 
                        
                    receiving_timer.cancel() 
                    print("Sending ACK for the whole message")
                    ACK=str.encode("00000")
                    socketServer.sendto(ACK, address)

                    lalala=0
                    final = ""
                    while (lalala!=number_of_fragments_receive): #reuniting the tuple in one string 
                        final+=msg[lalala]
                        lalala+=1
                    print(final) #printing the message, which have been sent

                else: #if it is a file
                    path = input("Enter where to save the file and its name(Desktop/file): ") #asking for the place where to save the file
                    mytimer_frag(gotten_numbers, j, last_come, address, number_of_fragments_receive)
                    receiving_timer.start()
                    j = 0
                    gotten_numbers= [False] * number_of_fragments_receive#this array will contain an ordinal numbers of fragments which came
                    last_come = 0 
                    fileInBytes = [] #saving the fragments in a tuple

                    while(number_of_fragments_come!=number_of_fragments_receive):
                        if(change_j ==1):
                            j = round(j/3)*3
                            change_j= 0
                        else: j+=1
                        msg_fragment1 = socketServer.recvfrom(MAX_fragmentSize) #receiving fragment of file
                        receiving_timer.cancel() 
                        msg_fragment = msg_fragment1[0]

                        llll=int.from_bytes(msg_fragment[5:7], byteorder="big")-12 #founding out length of data in the fragment
                        check_sum2=(msg_fragment[10:12]).decode()
                        check_sum3 = calc_checksum( md5(msg_fragment[12:12+llll]))

                        if(check_sum2 == check_sum3):  #if checksums are equal
                            in_order = int.from_bytes((msg_fragment[7:10]), byteorder="big") #founding out an ordinal number of data in the fragment
                            print(in_order)
                            fileInBytes.insert(in_order, (msg_fragment[12:12+llll])) #adding to the tuple
                            gotten_numbers[in_order]=True #adding as received
                            number_of_fragments_come+=1

                            if(in_order>last_come):
                                last_come=in_order
                            
                        if(((j % 3 == 0) & (j!=0))or (number_of_fragments_come==number_of_fragments_receive) ): #after receiving 3 fragments
                            print("Checking after 3")
                            request_numbers = ""
                            kakak = 0
                            while(kakak<last_come):
                                if(gotten_numbers[kakak]==False):
                                    request_numbers += str(kakak)+"+"
                                    print("Requested: " + str(kakak))
                                kakak+=1
                            if(request_numbers!=""): #if not all 3 fragments came
                                print("Requested numbers: " + request_numbers)
                                send_request(request_numbers, address)
                                time.sleep(3) 
                            else: #if all 3 fragments came
                                print("I just going to send ACK")
                                ACK=str.encode("00000")
                                socketServer.sendto(ACK, address)
                        mytimer_frag(gotten_numbers, j, last_come, address, number_of_fragments_receive)
                        receiving_timer.start() 
                        
                    receiving_timer.cancel() 
                    print("Sending ACK for the whole file")
                    x = thingToSend("00000", 12+ len(path+type_next), 0, 1, path+type_next, 1)
                    socketServer.sendto(x, address)

                    out_file = open(path+type_next, "ab") #creating file with appropriate type to save the received data
                    print(path+type_next)

                    lalala=0
                    final = bytearray()
                    while (lalala!=number_of_fragments_receive): #reuniting butes in one string
                        out_file.write(fileInBytes[lalala])
                        lalala+=1
                    out_file.close()
            # mytimer_connect_server(address)
            # connection_timer_ser.start()
            
            if(flag_con == 1):
                continue
            elif (flag_con==2):
                connection_timer_ser.cancel()
                break
        if(flag_bye==1):
            socketServer.close()
            break
        else:
            socketServer.close()
            pom = ServerIP
            ServerIP = clientIP
            ClientIP = pom
    
print("The program is finished. Thanks)))")



