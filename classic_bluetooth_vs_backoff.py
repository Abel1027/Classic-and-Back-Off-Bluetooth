import simpy
import random

def binary_to_decimal(b_num):
	return int(b_num, 2)

def decimal_to_binary(d_num):
	return bin(d_num)

def inquiry(env, index, backOff=False):
	############### Inquiry Inquiring ###############
	global channels
	global collisions
	global inquirer_energy
	global inquirer_end
	global found_time
	#off = 0
	off_list = [0, 16]
	off = random.choice(off_list)
	max_num_bits = 28
	clock = '0b'
	for i in range(max_num_bits):
		clock = clock + '0'

	counter = 0
	sent = False
	print_ = False
	rx = False
	# print('inquiry (' + str(index) + '): off=' + str(off) + ' at ' + str(env.now))
	back_off = random.randint(0, 10)
	yield env.timeout(31.25*back_off)
	while True:
		for step in range(10):
			if inquirer_end[index] == False:
				if step == 0:
					if len(list(clock)) < max_num_bits + 2:
						chunk = ''
						for j in range(max_num_bits + 2 - len(list(clock))):
							chunk = chunk + '0'
						clock = '0b' + chunk + clock.split('0b')[-1]
					CLK_16_12 = binary_to_decimal('0b' + clock[-17:-12])
					CLK_4_2_0 = binary_to_decimal('0b' + clock[-5:-2] + clock[-1])
					freq = (CLK_16_12 + off + (CLK_4_2_0 - CLK_16_12) % 16) % 32
					clock = decimal_to_binary(binary_to_decimal(clock) + 1)
					if counter == 0 or counter == 1:
						print_ = False
						if channels[freq] != '':
							collisions += 1
							# print('inquiry (' + str(index) + '): Collision #' + str(collisions) + ' at ' + str(env.now))
							channels[freq] = ''
						else:
							sent = True
							# print('inquiry (' + str(index) + '): ' + str(freq) + ' at ' + str(env.now))
							channels[freq] = 'inquiry_' + str(index)
							inquirer_energy += 1

					if counter == 2 or counter == 3:
						print_ = True
					counter += 1
					if counter > 3: counter = 0
				if print_ == True:
					# print('scan (' + str(index) + '): ' + str(freq) + ' at ' + str(env.now))
					if channels[freq].split('_')[0] == 'scan' and channels[freq].split('_')[1] == str(index):
						rx = True
						print('RELAY FOUND (' + channels[freq].split('_')[2] + ') !!! for inquirer (' + str(index) + ') at ' + str(env.now))
						found_time = env.now
				yield env.timeout(31.25)
				if rx == True:
					rx = False
					channels[freq] = ''
					inquirer_end[index] = True

				if sent == True:
					sent = False
					# print('CANCELLED by inquirer (' + str(index) + ') at ' + str(env.now))
					channels[freq] = ''
			else:
				yield env.timeout(31.25)
		if backOff == True:
			#after 11.25 ms generate backoff
			if counter%360 == 0:
				back_off = random.randint(0, 10)
				# print('inquiry (' + str(index) + ') back-off=' + str(31.25*back_off))
				yield env.timeout(31.25*back_off) # wait [0, ..., 10]*31.25 us to start again

def scanner(env, index):
	############### Scanner ###############
	global channels
	global collisions
	global scanner_energy
	global inquirer_end
	off = 0
	max_num_bits = 28
	clock = '0b'
	for i in range(max_num_bits):
		clock = clock + '0'

	counter = 0
	tx = False
	rx = False
	N = -1
	#N = random.randint(-1, 30) # 0 - 32
	#print('scanner (' + str(index) + '): N=' + str(N+1) + ' at ' + str(env.now))
	incoming_msg = ''
	#random start
	back_off = random.randint(0, 100)
	yield env.timeout(31.25*back_off)
	while True:
		for step in range(360):
			if False in inquirer_end:
				if step == 0:
					if len(list(clock)) < max_num_bits + 2:
						chunk = ''
						for j in range(max_num_bits + 2 - len(list(clock))):
							chunk = chunk + '0'
						clock = '0b' + chunk + clock.split('0b')[-1]
					CLK_16_12 = binary_to_decimal('0b' + clock[-17:-12])
					if clock[-1] == '0':
						N += 1
					freq = (CLK_16_12 + N) % 32
					clock = decimal_to_binary(binary_to_decimal(clock) + 2)
				# print('scanner (' + str(index) + '): ' + str(freq) + ' at ' + str(env.now))
				if rx == False and channels[freq].split('_')[0] == 'inquiry':
					incoming_msg = (channels[freq].split('_')[1] + '_' + str(counter))
					# print('DISCOVERY SIGNAL ARRIVED (' + str(index) + ') at ' + str(env.now))
					rx = True

				if rx == True and counter - int(incoming_msg.split('_')[1]) == 19:
					rx = False
					#transmit back
					if channels[freq] != '':
						collisions += 1
						# print('scanner (' + str(index) + '): Collision #' + str(collisions) + ' at ' + str(env.now))
						channels[freq] = ''
					else:
						channels[freq] = 'scan_' + incoming_msg.split('_')[0] + '_' + str(index)
						scanner_energy += 1
						tx = True

				yield env.timeout(31.25) # scan 360 times within 11.25 ms
				if tx == True:
					channels[freq] = ''
					# print('CANCELLED by scanner (' + str(index) + ') at ' + str(env.now))
					random_timer = random.randint(0, 127)*31.25*20
					# print('Random Timer (' + str(index) + '): ' + str(random_timer))
					yield env.timeout(random_timer) # wait [0,..., 127]*11.25 ms to scan again

				counter += 1
			else:
				yield env.timeout(31.25)
		rx = False
		tx = False
		# print('scanner (' + str(index) + ') waiting 0.64 s')
		yield env.timeout(40960/2*31.25) # wait 0.64 seconds to scan again

def main(totalInquirers, totalScanners, backOff, for_file):
	random.seed(7)

	global channels
	channels = ['' for i in range(32)]
	global collisions
	collisions = 0
	global inquirer_energy
	inquirer_energy = 0
	global scanner_energy
	scanner_energy = 0
	global inquirer_end
	inquirer_end = [False for i in range(totalInquirers)]
	global found_time
	found_time = 0

	print('Total Inquirers: ', totalInquirers)
	print('Total Scanners: ', totalScanners)
	print('Executing...')
	env = simpy.Environment()
	for inq_ix in range(totalInquirers):
		env.process(inquiry(env, inq_ix, backOff=backOff))
	for inq_ix in range(totalScanners):
		env.process(scanner(env, inq_ix))
	finish_time = 6*10**7 # 1 minute
	env.run(until=finish_time)
	print('----------Simulation complete----------')
	total_inq_find_sc = 0
	for i in inquirer_end:
		if i == True: total_inq_find_sc += 1
	if total_inq_find_sc != totalInquirers: found_time = finish_time
	print('Total inquirers that found a relay: ', total_inq_find_sc, ' of ', totalInquirers)
	print('Total collisions: ', collisions)
	print('Energy dropped by Inquirers Tx: ', inquirer_energy)
	print('Energy dropped by Scanners Tx: ', scanner_energy)

	if backOff == False:
		file = open('logs/classic' + for_file + '.log', 'a')
	else:
		file = open('logs/backoff' + for_file + '.log', 'a')
	file.write(str(totalInquirers) + '/' + str(totalScanners) + '|' + str(found_time) + '|' + str(total_inq_find_sc) + '|' + str(collisions) + '|' + str(inquirer_energy) + '|' + str(scanner_energy) + '\n')
	file.close()

if __name__ == '__main__':
	totalScanners = 50
	bOff = [True, False]
	for backOff in bOff:
		for i in range(10, 110, 10):
			print('back-off=' + str(backOff) + ' ##############################')
			main(i, totalScanners, backOff, '')

	totalInquirers = 50
	bOff = [True, False]
	for backOff in bOff:
		for i in range(10, 110, 10):
			print('back-off=' + str(backOff) + ' ##############################')
			main(totalInquirers, i, backOff, '2')