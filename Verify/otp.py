import random
def generateOtp(length):
    otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return otp
