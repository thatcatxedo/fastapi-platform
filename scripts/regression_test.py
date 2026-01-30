#!/usr/bin/env python3
"""
Regression test script for FastAPI Platform.

Tests the full user journey:
1. Sign up new user
2. Login and get token
3. Deploy a hello world app with database
4. Verify app is running
5. Test app endpoint and database connectivity
6. Clean up (delete app and user)

Usage:
    # Run from within the backend pod:
    kubectl exec -n fastapi-platform deployment/backend -- python3 /path/to/regression_test.py

    # Or copy to pod first:
    kubectl cp scripts/regression_test.py fastapi-platform/<pod>:/tmp/regression_test.py
    kubectl exec -n fastapi-platform deployment/backend -- python3 /tmp/regression_test.py

    # With cleanup disabled (keep test resources):
    kubectl exec -n fastapi-platform deployment/backend -- python3 /tmp/regression_test.py --no-cleanup
"""
import asyncio
import aiohttp
import json
import sys
import time
import uuid
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
TEST_USER_PREFIX = "regtest"

# Test app code with database connection
APP_CODE = '''from fastapi import FastAPI
from pymongo import MongoClient
from datetime import datetime
import os

app = FastAPI()

client = MongoClient(os.environ.get("PLATFORM_MONGO_URI", "mongodb://localhost:27017/test"))
db = client.get_default_database()
visits = db.visits

@app.get("/")
def hello():
    visit = {"timestamp": datetime.utcnow(), "message": "Hello World!"}
    visits.insert_one(visit)
    count = visits.count_documents({})
    return {"message": "Hello World!", "visit_count": count}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/db-test")
def db_test():
    """Verify database is working"""
    test_doc = {"test": True, "timestamp": datetime.utcnow()}
    result = db.test_collection.insert_one(test_doc)
    found = db.test_collection.find_one({"_id": result.inserted_id})
    db.test_collection.delete_one({"_id": result.inserted_id})
    return {"success": found is not None, "inserted_id": str(result.inserted_id)}
'''


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def log_step(step: str):
    print(f"\n{Colors.BLUE}▶ {step}{Colors.RESET}")


def log_success(msg: str):
    print(f"  {Colors.GREEN}✓ {msg}{Colors.RESET}")


def log_error(msg: str):
    print(f"  {Colors.RED}✗ {msg}{Colors.RESET}")


def log_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ {msg}{Colors.RESET}")


class RegressionTest:
    def __init__(self, cleanup: bool = True):
        self.cleanup = cleanup
        self.test_id = uuid.uuid4().hex[:8]
        self.username = f"{TEST_USER_PREFIX}_{self.test_id}"
        self.email = f"{self.username}@example.com"
        self.password = f"TestPass_{self.test_id}!"
        self.token = None
        self.user_id = None
        self.app_id = None
        self.app_url = None
        self.errors = []

    async def run(self):
        """Run all regression tests."""
        print(f"\n{'='*60}")
        print(f"FastAPI Platform Regression Test")
        print(f"Test ID: {self.test_id}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            await self.test_signup()
            await self.test_login()
            await self.test_deploy_app()
            await self.test_app_health()
            await self.test_app_endpoint()
            await self.test_database_connection()
        except Exception as e:
            log_error(f"Test failed with exception: {e}")
            self.errors.append(str(e))
        finally:
            if self.cleanup:
                await self.cleanup_resources()

        elapsed = time.time() - start_time
        self.print_summary(elapsed)

        return len(self.errors) == 0

    async def test_signup(self):
        """Test user signup."""
        log_step("Testing user signup")

        async with aiohttp.ClientSession() as session:
            payload = {
                "username": self.username,
                "email": self.email,
                "password": self.password
            }
            async with session.post(f"{API_BASE}/api/auth/signup", json=payload) as resp:
                result = await resp.json()
                if resp.status == 200:
                    self.user_id = result.get("id")
                    log_success(f"User created: {self.username} (id: {self.user_id})")
                else:
                    error = f"Signup failed: {result}"
                    log_error(error)
                    self.errors.append(error)
                    raise Exception(error)

    async def test_login(self):
        """Test user login."""
        log_step("Testing user login")

        async with aiohttp.ClientSession() as session:
            payload = {"username": self.username, "password": self.password}
            async with session.post(f"{API_BASE}/api/auth/login", json=payload) as resp:
                result = await resp.json()
                if resp.status == 200:
                    self.token = result.get("access_token")
                    log_success(f"Login successful, token obtained")
                else:
                    error = f"Login failed: {result}"
                    log_error(error)
                    self.errors.append(error)
                    raise Exception(error)

    async def test_deploy_app(self):
        """Test app deployment."""
        log_step("Testing app deployment")

        async with aiohttp.ClientSession() as session:
            payload = {
                "name": f"regtest-{self.test_id}",
                "code": APP_CODE,
                "env_vars": {}
            }
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.post(f"{API_BASE}/api/apps", json=payload, headers=headers) as resp:
                result = await resp.json()
                if resp.status == 200:
                    self.app_id = result.get("app_id")
                    self.app_url = result.get("deployment_url")
                    status = result.get("status")
                    log_success(f"App created: {self.app_id}")
                    log_info(f"URL: {self.app_url}")
                    log_info(f"Status: {status}")
                else:
                    error = f"Deploy failed: {result}"
                    log_error(error)
                    self.errors.append(error)
                    raise Exception(error)

        # Wait for deployment to be ready
        log_info("Waiting for deployment to be ready...")
        await self.wait_for_deployment()

    async def wait_for_deployment(self, timeout: int = 60):
        """Wait for app deployment to be ready."""
        start = time.time()
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            while time.time() - start < timeout:
                async with session.get(
                    f"{API_BASE}/api/apps/{self.app_id}/deploy-status",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("deployment_ready"):
                            log_success(f"Deployment ready in {time.time()-start:.1f}s")
                            return
                await asyncio.sleep(2)

        error = f"Deployment not ready after {timeout}s"
        log_error(error)
        self.errors.append(error)

    async def test_app_health(self):
        """Test app health endpoint."""
        log_step("Testing app health endpoint")

        # Use internal service URL
        service_url = f"http://app-{self.app_id}.fastapi-platform.svc.cluster.local"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{service_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        log_success(f"Health check passed: {result}")
                    else:
                        error = f"Health check failed: HTTP {resp.status}"
                        log_error(error)
                        self.errors.append(error)
            except Exception as e:
                error = f"Health check error: {e}"
                log_error(error)
                self.errors.append(error)

    async def test_app_endpoint(self):
        """Test app main endpoint."""
        log_step("Testing app main endpoint")

        service_url = f"http://app-{self.app_id}.fastapi-platform.svc.cluster.local"

        async with aiohttp.ClientSession() as session:
            try:
                # Make two requests to verify visit counting works
                for i in range(2):
                    async with session.get(service_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            log_success(f"Request {i+1}: visit_count={result.get('visit_count')}")
                        else:
                            error = f"Request {i+1} failed: HTTP {resp.status}"
                            log_error(error)
                            self.errors.append(error)
                    await asyncio.sleep(0.5)
            except Exception as e:
                error = f"Endpoint test error: {e}"
                log_error(error)
                self.errors.append(error)

    async def test_database_connection(self):
        """Test database connectivity via app endpoint."""
        log_step("Testing database connection")

        service_url = f"http://app-{self.app_id}.fastapi-platform.svc.cluster.local"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{service_url}/db-test", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            log_success(f"Database write/read/delete test passed")
                        else:
                            error = "Database test returned success=false"
                            log_error(error)
                            self.errors.append(error)
                    else:
                        error = f"DB test failed: HTTP {resp.status}"
                        log_error(error)
                        self.errors.append(error)
            except Exception as e:
                error = f"Database test error: {e}"
                log_error(error)
                self.errors.append(error)

    async def cleanup_resources(self):
        """Clean up test resources."""
        log_step("Cleaning up test resources")

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

            # Delete app
            if self.app_id:
                try:
                    async with session.delete(
                        f"{API_BASE}/api/apps/{self.app_id}",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            log_success(f"Deleted app: {self.app_id}")
                        else:
                            log_error(f"Failed to delete app: HTTP {resp.status}")
                except Exception as e:
                    log_error(f"Error deleting app: {e}")

            # Note: User deletion requires admin privileges
            # For now, just log that cleanup would require admin
            if self.user_id:
                log_info(f"User {self.username} ({self.user_id}) requires admin to delete")

    def print_summary(self, elapsed: float):
        """Print test summary."""
        print(f"\n{'='*60}")
        if len(self.errors) == 0:
            print(f"{Colors.GREEN}ALL TESTS PASSED{Colors.RESET}")
        else:
            print(f"{Colors.RED}TESTS FAILED ({len(self.errors)} errors){Colors.RESET}")
            for error in self.errors:
                print(f"  - {error}")
        print(f"Duration: {elapsed:.2f}s")
        print(f"{'='*60}\n")


async def main():
    cleanup = "--no-cleanup" not in sys.argv
    if not cleanup:
        print("Note: Cleanup disabled, test resources will be retained")

    test = RegressionTest(cleanup=cleanup)
    success = await test.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
