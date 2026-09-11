import json
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any


# =========================================================
# Approval Store Interface & Implementations
# =========================================================

class BaseApprovalStore(ABC):
    @abstractmethod
    def save(self, approval_id: str, data: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get(self, approval_id: str) -> dict[str, Any] | None:
        pass


class JsonFileApprovalStore(BaseApprovalStore):
    """
    Local JSON file storage for local development and testing.
    Thread-safe and atomic file persistence.
    """
    def __init__(self, file_path: str | None = None):
        self.file_path = file_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "approvals_db.json"
        )
        self._lock = threading.RLock()
        with self._lock:
            self.cache: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading approvals database from {self.file_path}: {e}")
            return {}

    def _persist(self) -> None:
        temp_path = f"{self.file_path}.tmp.{uuid4()}"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=4)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            print(f"Error saving approvals database to {self.file_path}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def save(self, approval_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self.cache[approval_id] = data
            self._persist()

    def get(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            if approval_id not in self.cache:
                self.cache.update(self._load())
            return self.cache.get(approval_id)


class FirestoreApprovalStore(BaseApprovalStore):
    """
    Google Cloud Firestore backend for scalable, stateless Cloud Run deployment.
    """
    def __init__(self, collection_name: str = "approval_requests"):
        self.collection_name = collection_name
        try:
            from google.cloud import firestore
            self.db = firestore.Client()
            print(f"Connected to Google Cloud Firestore collection: {self.collection_name}")
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore ({e}). Falling back to local file storage.")
            self.db = None

    def save(self, approval_id: str, data: dict[str, Any]) -> None:
        if self.db is None:
            raise RuntimeError("Firestore client is not initialized.")
        try:
            doc_ref = self.db.collection(self.collection_name).document(approval_id)
            doc_ref.set(data)
        except Exception as e:
            print(f"Error saving approval {approval_id} to Firestore: {e}")
            raise RuntimeError(f"Failed to save approval {approval_id} to Firestore: {e}") from e

    def get(self, approval_id: str) -> dict[str, Any] | None:
        if self.db is None:
            raise RuntimeError("Firestore client is not initialized.")
        try:
            doc_ref = self.db.collection(self.collection_name).document(approval_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error fetching approval {approval_id} from Firestore: {e}")
            raise RuntimeError(f"Failed to fetch approval {approval_id} from Firestore: {e}") from e


def _init_store() -> BaseApprovalStore:
    backend = os.getenv("STORAGE_BACKEND", "").strip().lower()
    if backend == "firestore":
        fs_store = FirestoreApprovalStore()
        if fs_store.db is not None:
            return fs_store
    return JsonFileApprovalStore()


# Active store instance
_STORE = _init_store()

# Backwards compatibility alias for code that references _APPROVAL_REQUESTS directly
if isinstance(_STORE, JsonFileApprovalStore):
    _APPROVAL_REQUESTS = _STORE.cache
else:
    _APPROVAL_REQUESTS = {}


def load_approvals() -> dict[str, dict[str, Any]]:
    """Legacy helper for loading approvals."""
    if isinstance(_STORE, JsonFileApprovalStore):
        return _STORE.cache
    elif isinstance(_STORE, FirestoreApprovalStore):
        if _STORE.db is None:
            raise RuntimeError("Firestore client is not initialized.")
        try:
            results = {}
            docs = _STORE.db.collection(_STORE.collection_name).stream()
            for doc in docs:
                results[doc.id] = doc.to_dict()
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to load approvals from Firestore: {e}") from e
    return {}


def save_approvals(approvals: dict[str, dict[str, Any]] | None = None) -> None:
    """Legacy helper for saving approvals."""
    if approvals is not None:
        for k, v in approvals.items():
            _STORE.save(k, v)
    elif isinstance(_STORE, JsonFileApprovalStore):
        _STORE._persist()


def set_store(store: BaseApprovalStore) -> None:
    """Allows runtime override or test mocking of the store."""
    global _STORE, _APPROVAL_REQUESTS
    _STORE = store
    if isinstance(store, JsonFileApprovalStore):
        _APPROVAL_REQUESTS = store.cache


# =========================================================
# Create Approval Request
# =========================================================

def create_approval_request(
    owner: str,
    repository: str,
    pull_request_number: int,
    commit_sha: str,
    proposed_fixes: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create a new approval request for AI-generated code fixes.

    This function DOES NOT apply any changes.
    It stores the proposed changes and waits for the user to approve them.
    """

    if not owner:
        raise ValueError("Repository owner is required.")

    if not repository:
        raise ValueError("Repository name is required.")

    if not pull_request_number:
        raise ValueError("Pull request number is required.")

    if not commit_sha:
        raise ValueError("Commit SHA is required.")

    if not isinstance(proposed_fixes, list):
        raise ValueError("proposed_fixes must be a list.")

    if not proposed_fixes:
        raise ValueError("At least one proposed fix is required.")

    approval_id = str(uuid4())

    approval_request = {
        "approval_id": approval_id,
        "owner": owner,
        "repository": repository,
        "pull_request_number": pull_request_number,
        "commit_sha": commit_sha,
        "proposed_fixes": proposed_fixes,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": None,
    }

    _STORE.save(approval_id, approval_request)
    if isinstance(_STORE, JsonFileApprovalStore):
        _APPROVAL_REQUESTS[approval_id] = approval_request

    print("=" * 60)
    print("APPROVAL REQUEST CREATED")
    print("=" * 60)
    print(f"Approval ID: {approval_id}")
    print(f"Repository: {owner}/{repository}")
    print(f"PR Number: {pull_request_number}")
    print(f"Commit SHA: {commit_sha}")
    print(f"Proposed fixes: {len(proposed_fixes)}")
    print("Status: pending")
    print("=" * 60)

    return approval_request


# =========================================================
# Get Approval Request
# =========================================================

def get_approval_request(
    approval_id: str,
) -> dict[str, Any] | None:
    """
    Retrieve an approval request using its ID.
    Returns None if the approval request does not exist.
    """
    if not approval_id:
        return None

    res = _STORE.get(approval_id)
    if res is None and approval_id in _APPROVAL_REQUESTS:
        return _APPROVAL_REQUESTS.get(approval_id)
    return res


# =========================================================
# Approve Request
# =========================================================

def approve_request(
    approval_id: str,
) -> dict[str, Any]:
    """
    Approve a pending code-change request.

    IMPORTANT:
    This function ONLY changes the approval status.
    It does NOT modify GitHub or apply code changes.
    """

    approval_request = get_approval_request(approval_id)

    if approval_request is None:
        raise ValueError("Approval request not found.")

    if approval_request["status"] == "approved":
        return approval_request

    if approval_request["status"] == "cancelled":
        raise ValueError("This approval request has been cancelled.")

    approval_request["status"] = "approved"
    approval_request["approved_at"] = datetime.now(timezone.utc).isoformat()

    _STORE.save(approval_id, approval_request)
    if isinstance(_STORE, JsonFileApprovalStore):
        _APPROVAL_REQUESTS[approval_id] = approval_request

    print("=" * 60)
    print("CODE CHANGES APPROVED")
    print("=" * 60)
    print(f"Approval ID: {approval_id}")
    print("Status: approved")
    print("=" * 60)

    return approval_request


# =========================================================
# Cancel Request
# =========================================================

def cancel_request(
    approval_id: str,
) -> dict[str, Any]:
    """
    Cancel a pending approval request.
    This does not modify GitHub.
    """

    approval_request = get_approval_request(approval_id)

    if approval_request is None:
        raise ValueError("Approval request not found.")

    if approval_request["status"] == "approved":
        raise ValueError("An approved request cannot be cancelled.")

    approval_request["status"] = "cancelled"

    _STORE.save(approval_id, approval_request)
    if isinstance(_STORE, JsonFileApprovalStore):
        _APPROVAL_REQUESTS[approval_id] = approval_request

    return approval_request


# =========================================================
# Check Approval Status
# =========================================================

def is_approved(
    approval_id: str,
) -> bool:
    """
    Check whether an approval request has been approved.
    """
    approval_request = get_approval_request(approval_id)

    if approval_request is None:
        return False

    return approval_request["status"] == "approved"