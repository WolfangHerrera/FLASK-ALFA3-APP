import bcrypt


def generateHashForPassword(password : str) :
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def validatePassword(password : str, hashedPassword : str) :
    return bcrypt.checkpw(password.encode('utf-8'), hashedPassword.encode('utf-8'))


def setRolByName(username : str) :
    rolesByUser = {}

    return rolesByUser.get(username, 'USER')