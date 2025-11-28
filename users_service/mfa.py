import time 
import uuid 
import random 
from typing import Dict, Optional


mfa_challenges = {}

class MFAError(Exception):
    """This error will be raised when the MFA challenge is invaled, expired or does not match"""
    pass

def _generate():
    """
    Generate a 5-digit numeric code.  like 018932
    
    """
    return f"{random.randint(0, 99999):06d}"

def create_mfa_challenge(user_id,purpose, ttl_seconds=300):  
    """
    Here we creaet a new MFA challege. 
    :param user_id: The user ID to create the challenge for.
    :param purpose: The purpose of the challenge (e.g., "login", "sensitive_action").
    :param ttl_seconds: Time to live for the challenge in seconds.
    :return: The challenge ID and the generated code.
    """

    now = time.time()
    challenge_id = str(uuid.uuid4())
    code = _generate()
    mfa_challenges[challenge_id] = {
        "user_id": user_id,
        "purpose": purpose,
        "code": code,
        "expires_at": now + ttl_seconds,  # Challenge valid for 5 minutes
        }
    print(f"CREATED challenge: {challenge_id} =>", mfa_challenges[challenge_id])

    return challenge_id, code


def verify_mfa_challenge(challenge_id, code, user_id, expected_purpose):
    """
    here we verify the issued challenge for a given user and purpose. 
    :param challenge_id: this Id returned by the creat_mfa_challenge
    :parama code: the 6 digit code issued to the user.
    :param user_id: The user ID to verify the challenge for.
    :param expected_purpose: The expected purpose of the challenge.
    :raises MFAError: if the challenge is invalid, expired, used, or does not match.
    :return: True if verification is successful.
    """
    print(f"VERIFYING with id={challenge_id}, current store:", mfa_challenges)

    data = mfa_challenges.get(challenge_id)
    if not data:
        raise MFAError("Invalid challenge ID.")

    if data["purpose"] != expected_purpose:
        raise MFAError("Challenge purpose does not match.")
    
    if str(data["user_id"]) != str(user_id):
        raise MFAError("Challenge does not belong to the user.")
    now  = time.time()
    if now > data["expires_at"]:
        raise MFAError("Challenge has expired.")
    if data["code"] != code:
        raise MFAError("Invalid challenge code.")
    mfa_challenges.pop(challenge_id, None)

    return True