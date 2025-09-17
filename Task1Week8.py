# Task1W8.py
import time
import uuid

class SessionManager:
    """
    A simple in-memory session manager to create, validate, and delete sessions.
    This class simulates session handling in a stateless environment.
    """

    def __init__(self, expiry_seconds: int):
        """
        Initializes the SessionManager.

        Args:
            expiry_seconds (int): The duration in seconds for which a session remains active.
        """
        if not isinstance(expiry_seconds, int) or expiry_seconds <= 0:
            raise ValueError("expiry_seconds must be a positive integer.")
        
        self.expiry_seconds = expiry_seconds
        self.sessions = {} # Stores session_id -> creation_timestamp
        print(f"SessionManager initialized with a {self.expiry_seconds}-second expiry. ⏳")

    def create_session(self, session_id: str) -> str:
        """
        Creates a new session and stores it with the current timestamp.

        Args:
            session_id (str): A unique identifier for the session.

        Returns:
            str: The session_id that was created.
        """
        current_time = time.time()
        self.sessions[session_id] = current_time
        print(f"✅ Session '{session_id}' created at timestamp {current_time:.2f}.")
        return session_id

    def is_session_active(self, session_id: str, sliding_expiration: bool = False) -> bool:
        """
        Checks if a session is active. If expired, it's deleted automatically.

        Args:
            session_id (str): The ID of the session to validate.
            sliding_expiration (bool): If True, resets the session's expiry time upon access.

        Returns:
            bool: True if the session is active, False otherwise.
        """
        if session_id not in self.sessions:
            print(f"❓ Session '{session_id}' not found.")
            return False

        creation_time = self.sessions[session_id]
        current_time = time.time()
        
        if current_time > (creation_time + self.expiry_seconds):
            print(f"❌ Session '{session_id}' expired. Deleting...")
            del self.sessions[session_id]
            return False
        
        # Bonus Challenge: Sliding Expiration
        if sliding_expiration:
            self.sessions[session_id] = current_time # Refresh the timestamp
            print(f"🔄 Session '{session_id}' is active and its expiration has been refreshed.")
        else:
            print(f"👍 Session '{session_id}' is active.")
            
        return True

    def delete_session(self, session_id: str) -> str:
        """
        Manually deletes a session.

        Args:
            session_id (str): The ID of the session to delete.

        Returns:
            str: "Deleted" if successful, "Not Found" otherwise.
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🗑️ Session '{session_id}' has been manually deleted.")
            return "Deleted"
        
        print(f"🔍 Session '{session_id}' could not be found for deletion.")
        return "Not Found"

# --- Main execution block to demonstrate usage ---
if __name__ == "__main__":
    # 1. Initialize the session manager with a short expiry time for testing (e.g., 5 seconds)
    session_manager = SessionManager(expiry_seconds=5)
    
    print("\n" + "="*40)
    print("SCENARIO 1: Session Creation and Expiration")
    print("="*40)
    
    # 2. Create a new session for a user (e.g., 'user_alice')
    alice_session = str(uuid.uuid4()) # Generate a unique ID
    session_manager.create_session(alice_session)

    # 3. Check if the session is active immediately
    session_manager.is_session_active(alice_session)

    # 4. Wait for a short duration (less than expiry) and check again
    print("\nWaiting for 3 seconds...")
    time.sleep(3)
    session_manager.is_session_active(alice_session)

    # 5. Wait for the session to expire
    print("\nWaiting for 3 more seconds (total 6 > 5) for the session to expire...")
    time.sleep(3)
    session_manager.is_session_active(alice_session) # This check will find it expired and delete it
    
    # 6. Verify that the session has been automatically deleted
    print(f"Current sessions: {session_manager.sessions}")


    print("\n" + "="*40)
    print("SCENARIO 2: Manual Deletion (Logout)")
    print("="*40)
    
    # 7. Create a new session for another user
    bob_session = str(uuid.uuid4())
    session_manager.create_session(bob_session)
    session_manager.is_session_active(bob_session)
    
    # 8. Manually delete Bob's session (simulating a logout)
    session_manager.delete_session(bob_session)

    # 9. Try to check Bob's session again
    session_manager.is_session_active(bob_session)
    print(f"Current sessions: {session_manager.sessions}")
    
    
    print("\n" + "="*40)
    print("BONUS CHALLENGE: Sliding Expiration")
    print("="*40)
    
    # 10. Create a session for Charlie
    charlie_session = str(uuid.uuid4())
    session_manager.create_session(charlie_session)
    
    # 11. Wait for 4 seconds, then access the session with sliding_expiration=True
    print("\nWaiting 4 seconds...")
    time.sleep(4)
    session_manager.is_session_active(charlie_session, sliding_expiration=True)
    
    # 12. Wait for another 4 seconds. Without sliding expiration, it would have expired (4+4 > 5).
    print("\nWaiting another 4 seconds...")
    time.sleep(4)
    # Because the session was refreshed at the 4-second mark, it is still active.
    session_manager.is_session_active(charlie_session)
    print(f"Current sessions: {session_manager.sessions}")