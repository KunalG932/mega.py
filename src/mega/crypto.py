from Crypto.Cipher import AES
import json
import base64
import struct
import binascii
import random
import sys
import codecs
from typing import List, Tuple, Union, Optional

# Python3 compatibility
if sys.version_info < (3, ):
    def makebyte(x: str) -> bytes:
        """Convert string to bytes in Python 2 compatibility mode."""
        return x

    def makestring(x: bytes) -> str:
        """Convert bytes to string in Python 2 compatibility mode."""
        return x
else:
    def makebyte(x: str) -> bytes:
        """Convert string to bytes in Python 3."""
        return codecs.latin_1_encode(x)[0]

    def makestring(x: bytes) -> str:
        """Convert bytes to string in Python 3."""
        return codecs.latin_1_decode(x)[0]


def aes_cbc_encrypt(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data using AES in CBC mode.
    
    Args:
        data: Data to encrypt
        key: Encryption key
        
    Returns:
        Encrypted data
    """
    if len(key) != 32:  # AES-256 requires 32-byte key
        raise ValueError("Key must be 32 bytes long")
    aes_cipher = AES.new(key, AES.MODE_CBC, makebyte('\0' * 16))
    return aes_cipher.encrypt(data)


def aes_cbc_decrypt(data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using AES in CBC mode.
    
    Args:
        data: Encrypted data
        key: Decryption key
        
    Returns:
        Decrypted data
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes long")
    aes_cipher = AES.new(key, AES.MODE_CBC, makebyte('\0' * 16))
    return aes_cipher.decrypt(data)


def aes_cbc_encrypt_a32(data: List[int], key: List[int]) -> List[int]:
    """
    Encrypt a32 data using AES in CBC mode.
    
    Args:
        data: Data as list of 32-bit integers
        key: Key as list of 32-bit integers
        
    Returns:
        Encrypted data as list of 32-bit integers
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    return str_to_a32(aes_cbc_encrypt(a32_to_str(data), a32_to_str(key)))


def aes_cbc_decrypt_a32(data: List[int], key: List[int]) -> List[int]:
    """
    Decrypt a32 data using AES in CBC mode.
    
    Args:
        data: Encrypted data as list of 32-bit integers
        key: Key as list of 32-bit integers
        
    Returns:
        Decrypted data as list of 32-bit integers
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    return str_to_a32(aes_cbc_decrypt(a32_to_str(data), a32_to_str(key)))


def stringhash(str: str, aeskey: List[int]) -> str:
    """
    Generate a hash of the string using AES.
    
    Args:
        str: Input string
        aeskey: AES key as list of 32-bit integers
        
    Returns:
        Base64 encoded hash
    """
    if len(aeskey) != 4:
        raise ValueError("AES key must be 4 integers long")
    s32 = str_to_a32(str)
    h32 = [0, 0, 0, 0]
    for i in range(len(s32)):
        h32[i % 4] ^= s32[i]
    for r in range(0x4000):
        h32 = aes_cbc_encrypt_a32(h32, aeskey)
    return a32_to_base64((h32[0], h32[2]))


def prepare_key(arr: List[int]) -> List[int]:
    """
    Prepare AES key from array.
    
    Args:
        arr: Input array of integers
        
    Returns:
        Prepared AES key as list of 4 integers
    """
    pkey = [0x93C467E3, 0x7DB0C7A4, 0xD1BE3F81, 0x0152CB56]
    if len(arr) % 4 != 0:
        raise ValueError("Input array length must be multiple of 4")
    for r in range(0x10000):
        for j in range(0, len(arr), 4):
            key = [0, 0, 0, 0]
            for i in range(4):
                if i + j < len(arr):
                    key[i] = arr[i + j]
            pkey = aes_cbc_encrypt_a32(pkey, key)
    return pkey


def encrypt_key(a: List[int], key: List[int]) -> List[int]:
    """
    Encrypt key using AES.
    
    Args:
        a: Data to encrypt as list of integers
        key: Encryption key as list of 4 integers
        
    Returns:
        Encrypted data as list of integers
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    return sum((aes_cbc_encrypt_a32(a[i:i + 4], key)
                for i in range(0, len(a), 4)), ())


def decrypt_key(a: List[int], key: List[int]) -> List[int]:
    """
    Decrypt key using AES.
    
    Args:
        a: Encrypted data as list of integers
        key: Decryption key as list of 4 integers
        
    Returns:
        Decrypted data as list of integers
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    return sum((aes_cbc_decrypt_a32(a[i:i + 4], key)
                for i in range(0, len(a), 4)), ())


def encrypt_attr(attr: dict, key: List[int]) -> bytes:
    """
    Encrypt attributes using AES.
    
    Args:
        attr: Dictionary of attributes
        key: Encryption key as list of 4 integers
        
    Returns:
        Encrypted attributes as bytes
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    attr_str = makebyte('MEGA' + json.dumps(attr))
    padding = b'\0' * (16 - len(attr_str) % 16)
    return aes_cbc_encrypt(attr_str + padding, a32_to_str(key))


def decrypt_attr(attr: bytes, key: List[int]) -> Optional[dict]:
    """
    Decrypt attributes using AES.
    
    Args:
        attr: Encrypted attributes as bytes
        key: Decryption key as list of 4 integers
        
    Returns:
        Decrypted attributes as dictionary or None if invalid
    """
    if len(key) != 4:
        raise ValueError("Key must be 4 integers long")
    try:
        decrypted = aes_cbc_decrypt(attr, a32_to_str(key))
        decrypted_str = makestring(decrypted).rstrip('\0')
        if decrypted_str[:6] == 'MEGA{"':
            return json.loads(decrypted_str[4:])
        return None
    except (ValueError, json.JSONDecodeError):
        return None


def a32_to_str(a: List[int]) -> bytes:
    """
    Convert list of 32-bit integers to bytes.
    
    Args:
        a: List of integers
        
    Returns:
        Bytes representation
    """
    return struct.pack('>%dI' % len(a), *a)


def str_to_a32(b: Union[str, bytes]) -> List[int]:
    """
    Convert bytes to list of 32-bit integers.
    
    Args:
        b: Input bytes or string
        
    Returns:
        List of 32-bit integers
    """
    if isinstance(b, str):
        b = makebyte(b)
    if len(b) % 4 != 0:
        b += b'\0' * (4 - len(b) % 4)
    return struct.unpack('>%dI' % (len(b) // 4), b)


def mpi_to_int(s):
    """
    A Multi-precision integer is encoded as a series of bytes in big-endian
    order. The first two bytes are a header which tell the number of bits in
    the integer. The rest of the bytes are the integer.
    """
    return int(binascii.hexlify(s[2:]), 16)


def extended_gcd(a, b):
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = extended_gcd(b % a, a)
        return (g, x - (b // a) * y, y)


def modular_inverse(a, m):
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    else:
        return x % m


def base64_url_decode(data):
    data += '=='[(2 - len(data) * 3) % 4:]
    for search, replace in (('-', '+'), ('_', '/'), (',', '')):
        data = data.replace(search, replace)
    return base64.b64decode(data)


def base64_to_a32(s):
    return str_to_a32(base64_url_decode(s))


def base64_url_encode(data):
    data = base64.b64encode(data)
    data = makestring(data)
    for search, replace in (('+', '-'), ('/', '_'), ('=', '')):
        data = data.replace(search, replace)
    return data


def a32_to_base64(a):
    return base64_url_encode(a32_to_str(a))


def get_chunks(size):
    p = 0
    s = 0x20000
    while p + s < size:
        yield (p, s)
        p += s
        if s < 0x100000:
            s += 0x20000
    yield (p, size - p)


def make_id(length):
    text = ''
    possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    for i in range(length):
        text += random.choice(possible)
    return text
