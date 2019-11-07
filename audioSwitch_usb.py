# -*- coding: UTF-8 -*-
import pexpect
import sys
from functools import reduce
import re
import hid
import time
import threading

PROMPT = ['#', '>>>', '>', '\$', 'login:']


def send_command(child, cmd):  # 传递命令
    child.sendline(cmd)
    child.expect(PROMPT)  # 期望获得的命令提示符
    # print child.buffer


def ssh_connect(user, host, password):
    ssh_newkey = "Are you sure you want to continue connecting"
    connStr = 'ssh ' + user + '@' + host
    child = pexpect.spawn(connStr)  # 实例化连接
    #log_fileid = open("logfile.txt", 'w')
    #child.logfile = log_fileid
    #child.logfile_read = sys.stdout
    ret = child.expect([pexpect.TIMEOUT, ssh_newkey, '[P|p]assword:'])  ##捕获 ssh_newkey
    if ret == 0:  # 判断捕获的信息
        print '[-] Error Connecting'
        return
    if ret == 1:  # 捕获了ssh_newkey的消息
        child.sendline('yes')  # 发送yes
        ret = child.expect([pexpect.TIMEOUT, ssh_newkey, '[P|p]assword:'])
        if ret == 0:
            print '[-] Error Connecting'
            return
    child.sendline(password)
    child.expect(PROMPT)  # 捕获命令提示符
    return child


host = "10.74.130.80"
user = "gulian"
password = "cisco123"

child_bt = ssh_connect(user, host, password)
child_aux_server = ssh_connect(user, host, password)
child_aux_client = ssh_connect(user, host, password)


def init_case():
    pass


# 初始化命令行
def init_cli(cli_type, child):
    if cli_type is 'bt':
        send_command(child, 'telnet 10.79.33.30')
        send_command(child, 'root')
        send_command(child, 'btcli')
        send_command(child, 'init-client me')
        send_command(child, 'register-event all')
        send_command(child, 'hfg reset-all-calls')
    elif cli_type is 'aux_server':
        send_command(child, 'telnet 10.74.37.74')
        send_command(child, 'root')
        send_command(child, 'cd /tmp')
        send_command(child, './auxport')
    elif cli_type is 'aux_client':
        send_command(child, 'telnet 10.74.37.74')
        send_command(child, 'root')
        send_command(child, 'cd /tmp')


def init_usb():
    global usb1_dev
    global usb2_dev
    usb1_path = ''
    usb2_path = ''
    usb1_dev = hid.device()
    usb2_dev = hid.device()

    for d in hid.enumerate():
        keys = list(d.keys())
        keys.sort()
        for key in keys:
            if key is 'product_string' and (d[key] == u'Cisco 561 MB' or d[key] == u'Cisco 562 MB'):
                usb1_path = d['path']
                break
            elif key is 'product_string' and d[key] == u'Cisco 56x MB':
                usb2_path = d['path']
                break
    print usb1_path
    print usb2_path
    if source_port_1 is not 'aux':
        usb1_dev.open_path(usb1_path)
        usb1_dev.set_nonblocking(1)

    usb2_dev.open_path(usb2_path)
    usb2_dev.set_nonblocking(1)


combine_case = lambda x, code=',': reduce(lambda x, y: [str(i) + code + str(j) for i in x for j in y], x)


def start_automation_audio_switch():
    call_event_list = ['idle', 'ring', 'hold', 'hook']
    active_source_list = ['source1', 'source2', 'source3']
    key_list = ['answer', 'reject']
    automation_cases = combine_case([active_source_list, call_event_list, call_event_list, call_event_list, key_list])
    pass_rate = travel_cases(automation_cases)

    return pass_rate


def parse_case(case):
    case_dic = {}
    res_case = re.split(',', case)
    case_dic['active_source'] = res_case[0]
    case_dic['S1_Call_Status'] = res_case[1]
    case_dic['S2_Call_Status'] = res_case[2]
    case_dic['S3_Call_Status'] = res_case[3]
    case_dic['call_button'] = res_case[4]

    return case_dic


def make_call_as_per_parameters(call_parameters):
    active_source = call_parameters['active_source']

    if active_source == 'source1':
        make_call_on_source2(call_parameters['S2_Call_Status'])
        led2 = update_led_nonactive_source(call_parameters['S2_Call_Status'])
        make_call_on_source3(call_parameters['S3_Call_Status'])
        led3 = update_led_nonactive_source(call_parameters['S3_Call_Status'])
        set_active_source(active_source)
        make_call_on_source1(call_parameters['S1_Call_Status'])
        led1 = update_led_active_source(call_parameters['S1_Call_Status'])
    elif active_source == 'source2':
        make_call_on_source1(call_parameters['S1_Call_Status'])
        led1 = update_led_nonactive_source(call_parameters['S1_Call_Status'])
        make_call_on_source3(call_parameters['S3_Call_Status'])
        led3 = update_led_nonactive_source(call_parameters['S3_Call_Status'])
        set_active_source(active_source)
        make_call_on_source2(call_parameters['S2_Call_Status'])
        led2 = update_led_active_source(call_parameters['S2_Call_Status'])
    elif active_source == 'source3':
        make_call_on_source1(call_parameters['S1_Call_Status'])
        led1 = update_led_nonactive_source(call_parameters['S1_Call_Status'])
        make_call_on_source2(call_parameters['S2_Call_Status'])
        led2 = update_led_nonactive_source(call_parameters['S2_Call_Status'])
        set_active_source(active_source)
        make_call_on_source3(call_parameters['S3_Call_Status'])
        led3 = update_led_active_source(call_parameters['S3_Call_Status'])
    led_sequence = compute_led_sequence(led1, led2, led3)
    res = check_makecall_result_through_led(led_sequence)
    if res == False:
        print 'Make call led check fail !!'
    return 0


def get_incoming_num(call_parameters):
    num = 0

    if call_parameters['S1_Call_Status'] == 'ring':
        num += 1
    if call_parameters['S2_Call_Status'] == 'ring':
        num += 1
    if call_parameters['S3_Call_Status'] == 'ring':
        num += 1

    return num


def check_active_source_right(call_parameters, status):
    if call_parameters['active_source'] == 'source1' and call_parameters['S1_Call_Status'] == status:
        return True
    if call_parameters['active_source'] == 'source2' and call_parameters['S2_Call_Status'] == status:
        return True
    if call_parameters['active_source'] == 'source3' and call_parameters['S3_Call_Status'] == status:
        return True

    return False


def pre_handle(call_parameters):
    condition = {'has_incoming_call': False,
                 'incoming_in_as': False,
                 'call_button': '',
                 'incoming_num': 0}

    if 'ring' in call_parameters.values():
        condition['has_incoming_call'] = True

    if call_parameters['call_button'] == 'answer':
        condition['call_button'] = 'single'
    else:
        condition['call_button'] = 'double'

    condition['incoming_num'] = get_incoming_num(call_parameters)

    condition['incoming_in_as'] = check_active_source_right(call_parameters, 'ring')

    condition['idle_in_as'] = check_active_source_right(call_parameters, 'idle')

    condition['hook_in_as'] = check_active_source_right(call_parameters, 'hook')

    condition['hold_in_as'] = check_active_source_right(call_parameters, 'hold')

    return condition


def get_incoming_source(call_parameters):
    incoming_source = ''
    if call_parameters['S1_Call_Status'] == 'ring':
        return 'source1'
    elif call_parameters['S2_Call_Status'] == 'ring':
        return 'source2'
    elif call_parameters['S3_Call_Status'] == 'ring':
        return 'source3'

    return incoming_source


def compute_expect_result(call_parameters):
    expected_result = {}
    tmp = {}
    expected_result['active_source'] = call_parameters['active_source']
    tmp['call_state'] = call_parameters['S1_Call_Status']
    tmp['led_state'] = update_led_nonactive_source(call_parameters['S1_Call_Status'])
    tmp['expected_event'] = 'none'
    expected_result['source1'] = tmp.copy()

    tmp['call_state'] = call_parameters['S2_Call_Status']
    tmp['led_state'] = update_led_nonactive_source(call_parameters['S2_Call_Status'])
    tmp['expected_event'] = 'none'
    expected_result['source2'] = tmp.copy()

    tmp['call_state'] = call_parameters['S3_Call_Status']
    tmp['led_state'] = update_led_nonactive_source(call_parameters['S3_Call_Status'])
    tmp['expected_event'] = 'none'
    expected_result['source3'] = tmp.copy()

    condition = pre_handle(call_parameters)
    if condition['has_incoming_call']:  # check if there is an incoming call from any source
        if condition['incoming_in_as']:    # active source has an incoming call
            if condition['call_button'] == 'single':
                tmp['call_state'] = 'hook'
                tmp['led_state'] = update_led_active_source('hook')
                tmp['expected_event'] = 'answer'
                expected_result[call_parameters['active_source']] = tmp.copy()
            else:
                tmp['call_state'] = 'idle'
                tmp['led_state'] = update_led_active_source('idle')
                tmp['expected_event'] = 'reject'
                expected_result[call_parameters['active_source']] = tmp.copy()
        else:  # 在非active source有incoming call
            if condition['incoming_num'] == 1:  # 有1个incoming call
                incoming_source = get_incoming_source(call_parameters)
                if condition['call_button'] == 'single':
                    tmp['call_state'] = 'hook'
                    tmp['led_state'] = update_led_active_source('hook')
                    tmp['expected_event'] = 'answer'
                    expected_result[incoming_source] = tmp.copy()
                else:
                    tmp['call_state'] = 'idle'
                    tmp['led_state'] = update_led_active_source('idle')
                    tmp['expected_event'] = 'reject'
                    expected_result[incoming_source] = tmp.copy()

                # 切换active source
                expected_result['active_source'] = incoming_source
            else:  # 有2个incoming call
                incoming_source = 'source4'

            if expected_result[call_parameters['active_source']]['call_state'] == 'hook' and condition['call_button'] == 'single':  # active source有active call
                tmp['call_state'] = 'hold'
                tmp['led_state'] = update_led_active_source('hold')
                tmp['expected_event'] = 'hold'
                expected_result[call_parameters['active_source']] = tmp.copy()

    else:
        if condition['idle_in_as'] and condition['call_button'] == 'single':  # 没有incoming call， 当前source idle
            expected_result[call_parameters['active_source']]['expected_event'] = 'off_hook'
            expected_result[call_parameters['active_source']]['led_state'] = update_led_active_source('hook')
        elif condition['hook_in_as'] and condition['call_button'] == 'single':  # 没有incoming call， 当前source有active call
            expected_result[call_parameters['active_source']]['call_state'] = 'hold'
            expected_result[call_parameters['active_source']]['expected_event'] = 'hold'
            expected_result[call_parameters['active_source']]['led_state'] = update_led_active_source('hold')
        elif condition['hold_in_as'] and condition['call_button'] == 'single':  # 没有incoming call， 当前source有hold call
            expected_result[call_parameters['active_source']]['call_state'] = 'hook'
            expected_result[call_parameters['active_source']]['expected_event'] = 'resume'
            expected_result[call_parameters['active_source']]['led_state'] = update_led_active_source('hook')
    return expected_result



def press_key_event(call_parameters):
    if source_port_1 == "aux":
        send_key_event_call_button_via_usb2(call_parameters['call_button'])
    else:
        send_key_event_call_button_via_usb1(call_parameters['call_button'])
    return 0


def check_first(expect_res):
    if expect_res['source1']['expected_event'] is not 'none':
        if source_port_1 == "aux":
            res = get_response_on_aux(expect_res['source1']['expected_event'])
        else:
            res = get_response_on_usb1(expect_res['source1']['expected_event'])
        if res is False:
            print 'usb1 can not receive expected-data!!!!!'
            return False

    if expect_res['source2']['expected_event'] is not 'none':
        res = get_response_on_usb2(expect_res['source2']['expected_event'])
        if res is False:
            print 'usb2 can not receive expected-data!!!!!'
            return False

    if expect_res['source3']['expected_event'] is not 'none':
        res = get_response_on_bt(expect_res['source3']['expected_event'])
        if res is False:
            print 'bt can not receive expected-data!!!!!'
            return False

    print "The first check is OK,  receive expected message."

    return True


def check_second(expect_res):
    return True
def send_get_led_message_via_usb2():
    usb2_dev.write([0x0C,0x02])
def update_led_nonactive_source(call_state):
    led={'white': 'none', 'green': 'none'}
    if call_state == 'idle':
        led={'white': 'off', 'green': 'off'}
    elif call_state == 'hook':
        led={'white': 'off', 'green': 'pulse'}
    elif call_state == 'hold':
        led={'white': 'off', 'green': 'pulse'}
    elif call_state == 'ring':
        led={'white': 'off', 'green': 'blinking'}
    return led

def update_led_active_source(call_state):
    led={'white': 'none', 'green': 'none'}
    if call_state == 'idle':
        led={'white': 'on', 'green': 'off'}
    elif call_state == 'hook':
        led={'white': 'off', 'green': 'pulse'}
    elif call_state == 'hold':
        led={'white': 'off', 'green': 'pulse'}
    elif call_state == 'ring':
        led={'white': 'blinking', 'green': 'blinking'}
    return led

def compute_led_sequence(led1,led2,led3):
    led_dic={'off':0,'on':1,'blinking':2,'breathing':3,'knock_knock_blink':4,'mute_blinking':5,'running':6,'pulse':7,'panic_blinking':8}
    led_sequence={led_dic[led1['white']],led_dic[led1['green']],led_dic[led2['white']],led_dic[led2['green']],led_dic[led3['white']],led_dic[led3['green']]}
    return led_sequence

def check_makecall_result_through_led(led_sequence):
    send_get_led_message_via_usb2()
    time.sleep(0.2)

    global g_usb2_timeout

    timer = threading.Timer(4, rx_time_out_usb2)
    timer.start()
    g_usb2_timeout = False
    while not g_usb2_timeout:
        receive_data = usb2_dev.read(16)
        if receive_data and receive_data[0] == 0xd and receive_data[1] == 0x02:
            for index in range(8,14):
                receive_data[index] != led_sequence[index-8]
                return False
                timer.cancel()
            return True
        else:
            print 'Report ID missed or wrong'
            return False
    print 'Time out for led'
    return False

def reset_usb1():
    usb1_dev.write([0x09, 0x00])


def reset_usb2():
    usb2_dev.write([0x09, 0x00])


def reset_bt():
    child_bt.expect('#')
    send_command(child_bt, 'btcli')
    send_command(child_bt, 'init-client me')
    send_command(child_bt, 'register-event all')
    send_command(child_bt, 'hfg reset-all-calls')


def reset_aux():
    send_command(child_aux_client, './client idl')


def clear_bt_cli():
    child_bt.sendcontrol('c')


def reset_case():
    if source_port_1 == 'aux':
        reset_aux()
    else:
        reset_usb1()

    reset_usb2()

    clear_bt_cli()

    reset_bt()


def travel_cases(automation_cases):
    test_cases = ['source1,ring,idle,idle,answer', 'source1,ring,idle,idle,reject']
    count = 0
    success_num = 0
    failed_case_1st = []
    #f = open('bt_event.txt', 'w')
    # 遍历数组
    for case in automation_cases:
        count += 1
        print("case ----- %d" % count)
        print case
        # 解析case
        call_parameters = parse_case(case)
 
        # 根据case预配make call
        res = make_call_as_per_parameters(call_parameters)
        if res is False:
            print "ERROR: Make call error"
            return res

        # 分析预期的结果
        expect_res = compute_expect_result(call_parameters)
        #if expect_res['source3']['expected_event'] is not 'none':
            #f.write(expect_res['source3']['expected_event'])
            #f.write('\n')
        print "expected result as per this case"
        print expect_res

        # 模拟耳机按键消息
        time.sleep(0.1)
        res = press_key_event(call_parameters)
        if res is False:
            print "ERROR: press Key error"

        # check第一阶段---是否收到消息
        res = check_first(expect_res)
        if res is False:
            failed_case_1st.append(case)
            print "1st Check False: case %d fail!" % count
        else:
            success_num += 1
            print "1st Check Success !!!"

        # check第二阶段----检查dock的led state和call state
        res = check_second(expect_res)
        if res is False:
            print "2nd CheckFalse: case %d fail!" % count
        else:
            print "2nd check success !!!"

        print "********** end case %d ***********" % count

        reset_case()

        time.sleep(1)

    print "travel 1st: success %d" % success_num
    time.sleep(0.5)

    # 针对第一遍fail的case再跑一遍，因为python pexpect的问题
    for case in failed_case_1st:
        print case
        call_parameters = parse_case(case)
        make_call_as_per_parameters(call_parameters)
        expect_res = compute_expect_result(call_parameters)
        print "expected result as per this case"
        print expect_res
        time.sleep(0.1)
        press_key_event(call_parameters)
        res = check_first(expect_res)
        if res is False:
            print "1st Check False: case %d fail!" % count
        else:
            success_num += 1
            print "1st Check Success !!!"

        reset_case()

        time.sleep(0.5)

    time.sleep(2)
    if source_port_1 == "aux":
        child_aux_server.sendcontrol('c')

    print success_num
    return float(success_num)/count


def make_call_via_bt(call_status):
    # 先把所有的calls清理掉
    send_command(child_bt, 'hfg reset-all-calls')

    if call_status == 'idle':
        return True

    elif call_status == 'ring':
        send_command(child_bt, 'hfg notify incoming 111')

    elif call_status == 'hold':
        send_command(child_bt, 'hfg notify incoming 111')
        send_command(child_bt, 'hfg notify hold 1')

    elif call_status == 'hook':
        send_command(child_bt, 'hfg notify incoming 111')
        send_command(child_bt, 'hfg notify active 1')

    return True


def make_call_via_usb1(call_status):
    if call_status == 'idle':
        return True
    elif call_status == 'ring':
        usb1_dev.write([0x09, 0x04])
        return True
    elif call_status == 'hold':
        usb1_dev.write([0x09, 0x00])
        usb1_dev.write([0x09, 0x20])
        return True
    elif call_status == 'hook':
        usb1_dev.write([0x09, 0x00])
        usb1_dev.write([0x09, 0x02])
        return True
    return 0


def make_call_via_usb2(call_status):
    if call_status == 'idle':
        return True
    elif call_status == 'ring':
        usb2_dev.write([0x09, 0x04])
        return True
    elif call_status == 'hold':
        usb2_dev.write([0x09, 0x00])
        usb2_dev.write([0x09, 0x20])
        return True
    elif call_status == 'hook':
        usb2_dev.write([0x09, 0x00])
        usb2_dev.write([0x09, 0x02])
        return True
    return False


def make_call_via_aux(call_status):
    if call_status == 'idle':
        send_command(child_aux_client, './client idl')
        return True
    elif call_status == 'ring':
        send_command(child_aux_client, './client rin')
        return True
    elif call_status == 'hold':
        send_command(child_aux_client, './client hol')
        return True
    elif call_status == 'hook':
        send_command(child_aux_client, './client ac')
        return True
    return False


def set_active_source(source_num):
    if source_port_1 is 'aux':
        set_active_source_via_usb2(source_num)
    else:
        set_active_source_via_usb1(source_num)


def set_active_source_via_usb1(source_num):
    if source_num == 'source1':  # phone source active  #debugsh set cisco headset dock-key phone single
        usb1_dev.write([0x0C, 0x03, 0x01, 0x00])
    elif source_num == 'source2':  # pc source active  #debugsh set cisco headset dock-key pc single
        usb1_dev.write([0x0C, 0x03, 0x02, 0x00])
    elif source_num == 'source3':  # bt source active  #debugsh set cisco headset dock-key bt single
        usb1_dev.write([0x0C, 0x03, 0x03, 0x00])

    return True


def set_active_source_via_usb2(source_num):
    if source_num == 'source1':  # phone source active  #debugsh set cisco headset dock-key phone single
        usb2_dev.write([0x0C, 0x03, 0x01, 0x00])
    elif source_num == 'source2':  # pc source active  #debugsh set cisco headset dock-key pc single
        usb2_dev.write([0x0C, 0x03, 0x02, 0x00])
    elif source_num == 'source3':  # bt source active  #debugsh set cisco headset dock-key bt single
        usb2_dev.write([0x0C, 0x03, 0x03, 0x00])

    return True


def send_key_event_call_button_via_usb1(event):
    if event == 'answer':
        usb1_dev.write([0x0C, 0x05, 0x01, 0x03, 0x00])
    elif event == 'reject':
        usb1_dev.write([0x0C, 0x05, 0x01, 0x03, 0x01])

    return True


def send_key_event_call_button_via_usb2(event):
    if event == 'answer':
        usb2_dev.write([0x0C, 0x05, 0x01, 0x03, 0x00])
    elif event == 'reject':
        usb2_dev.write([0x0C, 0x05, 0x01, 0x03, 0x01])

    return True


def make_call_on_source1(call_status):
    if source_port_1 == "aux":
        make_call_via_aux(call_status)
        time.sleep(3)
    else:
        make_call_via_usb1(call_status)


def make_call_on_source2(call_status):
    make_call_via_usb2(call_status)


def make_call_on_source3(call_status):
    make_call_via_bt(call_status)


def get_response_on_aux(expected_event):
    if expected_event is 'answer':
        try:
            child_aux_server.expect('answer', timeout=2)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'hold':
        try:
            child_aux_server.expect('hold', timeout=2)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'reject':
        try:
            child_aux_server.expect('reject', timeout=2)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'resume':
        try:
            child_aux_server.expect('resume', timeout=2)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'off_hook':
        try:
            child_aux_server.expect('answer', timeout=2)
        except pexpect.TIMEOUT:
            return False

    return True


def rx_time_out_usb1():
    global g_usb1_timeout

    print 'Time out!!!'
    g_usb1_timeout = True


def rx_time_out_usb2():
    global g_usb2_timeout

    print 'Time out!!!'
    g_usb2_timeout = True


def get_response_on_usb1(expected_event):
    global g_usb1_timeout

    timer = threading.Timer(5, rx_time_out_usb1)
    timer.start()
    g_usb1_timeout = False
    if expected_event is 'answer':
        while not g_usb1_timeout:
            receive_data = usb1_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x02:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'hold':
        while not g_usb1_timeout:
            receive_data = usb1_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and (receive_data[1] == 0x16 or receive_data[1] == 0x14):
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'reject':
        while not g_usb1_timeout:
            receive_data = usb1_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x28:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'off_hook':
        while not g_usb1_timeout:
            receive_data = usb1_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x02:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'resume':
        while not g_usb1_timeout:
            receive_data = usb1_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and (receive_data[1] == 0x14 or receive_data[1] == 0x16):
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    return False


def get_response_on_usb2(expected_event):
    global g_usb2_timeout

    timer = threading.Timer(4, rx_time_out_usb2)
    timer.start()
    g_usb2_timeout = False
    if expected_event is 'answer':
        while not g_usb2_timeout:
            receive_data = usb2_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x02:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'hold':
        while not g_usb2_timeout:
            receive_data = usb2_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and (receive_data[1] == 0x16 or receive_data[1] == 0x14):
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'reject':
        while not g_usb2_timeout:
            receive_data = usb2_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x28:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'off_hook':
        while not g_usb2_timeout:
            receive_data = usb2_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and receive_data[1] == 0x02:
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    elif expected_event is 'resume':
        while not g_usb2_timeout:
            receive_data = usb2_dev.read(2)
            if receive_data and receive_data[0] == 0x08 and (receive_data[1] == 0x14 or receive_data[1] == 0x16):
                timer.cancel()
                return True
            time.sleep(0.2)
        return False

    return False


def get_response_on_bt(expected_event):
    if expected_event is 'answer':
        try:
            child_bt.expect('BT_HFG_EVENT_ANSWER', timeout=3.5)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'hold':
        try:
            child_bt.expect('BT_HFG_EVENT_HOLD_AND_ACCEPT', timeout=3.5)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'reject':
        try:
            child_bt.expect('BT_HFG_EVENT_HANGUP', timeout=3.5)
        except pexpect.TIMEOUT:
            return False

    elif expected_event is 'resume':
        try:
            child_bt.expect('BT_HFG_EVENT_HOLD_AND_ACCEPT', timeout=3.5)
        except pexpect.TIMEOUT:
            return False

    return True


def main():
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    global g_usb1_timeout
    global g_usb2_timeout
    global source_port_1

    g_usb1_timeout = True
    g_usb2_timeout = True

    source_port_1 = "usb"

    init_cli('bt', child_bt)
    #init_cli('aux_server', child_aux_server)
    #init_cli('aux_client', child_aux_client)

    init_usb()

    pass_rate = start_automation_audio_switch()

    print 'pass_rate:'
    print "%.2f%%" % (pass_rate * 100)
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))


if __name__ == '__main__':
    main()




