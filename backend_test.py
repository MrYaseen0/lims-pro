#!/usr/bin/env python3
"""
Laboratory Information System (LIS) Backend API Testing
Tests all core functionality including authentication, patients, tests, orders, samples, results, pathologist workflow, reports, billing, and analytics.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class LISAPITester:
    def __init__(self, base_url="https://diagnosio-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.token = None
        self.headers = {'Content-Type': 'application/json'}
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data storage
        self.test_data = {
            'users': {},
            'patients': {},
            'tests': {},
            'orders': {},
            'samples': {},
            'invoices': {}
        }

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            'name': name,
            'success': success,
            'details': details,
            'response_data': response_data
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> tuple:
        """Make API request and return (success, response_data, status_code)"""
        url = f"{self.api_base}/{endpoint}"
        headers = self.headers.copy()
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return response.status_code in [200, 201], response_data, response.status_code
        except Exception as e:
            return False, str(e), 0

    def test_seed_data(self):
        """Test seeding demo data"""
        print("\n🌱 Testing Seed Data...")
        success, data, status = self.make_request('POST', 'seed')
        self.log_test("Seed demo data", success, f"Status: {status}", data)
        return success

    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication...")
        
        # Test admin login
        login_data = {"email": "admin@lims.pro", "password": "admin123"}
        success, data, status = self.make_request('POST', 'auth/login', login_data)
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            self.test_data['users']['admin'] = data['user']
            self.log_test("Admin login", True, f"Token received, Role: {data['user']['role']}")
        else:
            self.log_test("Admin login", False, f"Status: {status}, Data: {data}")
            return False

        # Test get current user
        success, data, status = self.make_request('GET', 'auth/me')
        self.log_test("Get current user", success, f"Status: {status}")

        # Test technician login
        tech_login = {"email": "technician@lims.pro", "password": "password123"}
        success, data, status = self.make_request('POST', 'auth/login', tech_login)
        if success:
            self.test_data['users']['technician'] = data
            self.log_test("Technician login", True, f"Role: {data['user']['role']}")
        else:
            self.log_test("Technician login", False, f"Status: {status}")

        # Test pathologist login
        path_login = {"email": "pathologist@lims.pro", "password": "password123"}
        success, data, status = self.make_request('POST', 'auth/login', path_login)
        if success:
            self.test_data['users']['pathologist'] = data
            self.log_test("Pathologist login", True, f"Role: {data['user']['role']}")
        else:
            self.log_test("Pathologist login", False, f"Status: {status}")

        return True

    def test_patients(self):
        """Test patient management"""
        print("\n👥 Testing Patient Management...")
        
        # Create patient
        patient_data = {
            "name": "John Test Patient",
            "age": 35,
            "gender": "male",
            "phone": "+1234567890",
            "email": "john.test@example.com",
            "address": "123 Test Street, Test City"
        }
        success, data, status = self.make_request('POST', 'patients', patient_data)
        if success:
            self.test_data['patients']['john'] = data
            patient_id = data['id']
            self.log_test("Create patient", True, f"Patient ID: {data['patient_id']}")
        else:
            self.log_test("Create patient", False, f"Status: {status}, Data: {data}")
            return False

        # Get all patients
        success, data, status = self.make_request('GET', 'patients')
        self.log_test("Get all patients", success and len(data) > 0, f"Found {len(data) if success else 0} patients")

        # Search patients
        success, data, status = self.make_request('GET', 'patients', params={'search': 'John'})
        self.log_test("Search patients by name", success and len(data) > 0, f"Found {len(data) if success else 0} patients")

        # Get patient by ID
        success, data, status = self.make_request('GET', f'patients/{patient_id}')
        self.log_test("Get patient by ID", success, f"Status: {status}")

        return True

    def test_test_catalog(self):
        """Test test catalog management"""
        print("\n🧪 Testing Test Catalog...")
        
        # Get all tests (should be seeded)
        success, data, status = self.make_request('GET', 'tests')
        if success and len(data) > 0:
            self.test_data['tests']['available'] = data
            self.log_test("Get all tests", True, f"Found {len(data)} tests")
        else:
            self.log_test("Get all tests", False, f"Status: {status}")
            return False

        # Get test categories
        success, data, status = self.make_request('GET', 'test-categories')
        self.log_test("Get test categories", success and len(data) > 0, f"Found {len(data) if success else 0} categories")

        # Create new test
        test_data = {
            "name": "Custom Test",
            "code": "CUSTOM001",
            "category": "Custom",
            "sample_type": "blood",
            "price": 75.0,
            "turn_around_time": 12,
            "description": "Custom test for testing"
        }
        success, data, status = self.make_request('POST', 'tests', test_data)
        if success:
            self.test_data['tests']['custom'] = data
            self.log_test("Create new test", True, f"Test ID: {data['id']}")
        else:
            self.log_test("Create new test", False, f"Status: {status}, Data: {data}")

        return True

    def test_orders(self):
        """Test order management"""
        print("\n📋 Testing Order Management...")
        
        if not self.test_data['patients'].get('john') or not self.test_data['tests'].get('available'):
            self.log_test("Order prerequisites", False, "Missing patient or test data")
            return False

        patient_id = self.test_data['patients']['john']['id']
        available_tests = self.test_data['tests']['available']
        
        # Select first 3 tests for order
        selected_tests = []
        for test in available_tests[:3]:
            selected_tests.append({
                "test_id": test['id'],
                "test_name": test['name'],
                "test_code": test['code'],
                "price": test['price']
            })

        # Create order
        order_data = {
            "patient_id": patient_id,
            "tests": selected_tests,
            "priority": "normal",
            "referring_doctor": "Dr. Test Doctor",
            "notes": "Test order for API testing"
        }
        success, data, status = self.make_request('POST', 'orders', order_data)
        if success:
            self.test_data['orders']['main'] = data
            order_id = data['id']
            self.log_test("Create order", True, f"Order ID: {data['order_id']}, Total: ${data['total_amount']}")
        else:
            self.log_test("Create order", False, f"Status: {status}, Data: {data}")
            return False

        # Get all orders
        success, data, status = self.make_request('GET', 'orders')
        self.log_test("Get all orders", success and len(data) > 0, f"Found {len(data) if success else 0} orders")

        # Get order by ID
        success, data, status = self.make_request('GET', f'orders/{order_id}')
        self.log_test("Get order by ID", success, f"Status: {status}")

        # Get orders by status
        success, data, status = self.make_request('GET', 'orders', params={'status': 'registered'})
        self.log_test("Get orders by status", success, f"Found {len(data) if success else 0} registered orders")

        return True

    def test_samples(self):
        """Test sample management"""
        print("\n🧫 Testing Sample Management...")
        
        if not self.test_data['orders'].get('main'):
            self.log_test("Sample prerequisites", False, "Missing order data")
            return False

        order_id = self.test_data['orders']['main']['id']
        
        # Create sample
        sample_data = {
            "order_id": order_id,
            "sample_type": "blood"
        }
        success, data, status = self.make_request('POST', 'samples', sample_data)
        if success:
            self.test_data['samples']['main'] = data
            sample_id = data['id']
            self.log_test("Collect sample", True, f"Sample ID: {data['sample_id']}, Barcode: {data['barcode']}")
        else:
            self.log_test("Collect sample", False, f"Status: {status}, Data: {data}")
            return False

        # Get all samples
        success, data, status = self.make_request('GET', 'samples')
        self.log_test("Get all samples", success and len(data) > 0, f"Found {len(data) if success else 0} samples")

        # Update sample status
        success, data, status = self.make_request('PUT', f'samples/{sample_id}/status', params={'status': 'received'})
        self.log_test("Update sample status", success, f"Status: {status}")

        return True

    def test_technician_workflow(self):
        """Test technician workflow"""
        print("\n🔬 Testing Technician Workflow...")
        
        # Switch to technician token
        if self.test_data['users'].get('technician'):
            self.token = self.test_data['users']['technician'].get('access_token')

        # Get technician queue
        success, data, status = self.make_request('GET', 'technician/queue')
        if success and len(data) > 0:
            self.log_test("Get technician queue", True, f"Found {len(data)} orders in queue")
            
            # Enter result for first test in first order
            order = data[0]
            if order.get('tests') and len(order['tests']) > 0:
                test = order['tests'][0]
                result_data = {
                    "order_id": order['id'],
                    "test_id": test['test_id'],
                    "values": {
                        "result": "Normal",
                        "value": "12.5",
                        "unit": "mg/dL",
                        "reference_range": "10-15 mg/dL"
                    },
                    "is_abnormal": False,
                    "technician_notes": "Test completed successfully"
                }
                success, data, status = self.make_request('POST', 'results', result_data)
                self.log_test("Enter test result", success, f"Status: {status}")
            else:
                self.log_test("Enter test result", False, "No tests found in order")
        else:
            self.log_test("Get technician queue", False, f"Status: {status}")

        # Switch back to admin token
        if self.test_data['users'].get('admin'):
            self.token = self.test_data['users']['admin']['access_token']

        return True

    def test_pathologist_workflow(self):
        """Test pathologist workflow"""
        print("\n👨‍⚕️ Testing Pathologist Workflow...")
        
        # Switch to pathologist token
        if self.test_data['users'].get('pathologist'):
            self.token = self.test_data['users']['pathologist']['access_token']

        # Get pathologist queue
        success, data, status = self.make_request('GET', 'pathologist/queue')
        if success and len(data) > 0:
            self.log_test("Get pathologist queue", True, f"Found {len(data)} orders for review")
            
            # Approve result for first test in first order
            order = data[0]
            if order.get('tests') and len(order['tests']) > 0:
                test = order['tests'][0]
                approval_data = {
                    "order_id": order['id'],
                    "test_id": test['test_id'],
                    "approved": True,
                    "pathologist_notes": "Results reviewed and approved"
                }
                success, data, status = self.make_request('POST', 'approve', approval_data)
                self.log_test("Approve test result", success, f"Status: {status}")
            else:
                self.log_test("Approve test result", False, "No tests found in order")
        else:
            self.log_test("Get pathologist queue", False, f"Status: {status}")

        # Switch back to admin token
        if self.test_data['users'].get('admin'):
            self.token = self.test_data['users']['admin']['access_token']

        return True

    def test_reports(self):
        """Test report management"""
        print("\n📄 Testing Report Management...")
        
        if not self.test_data['orders'].get('main'):
            self.log_test("Report prerequisites", False, "Missing order data")
            return False

        order_id = self.test_data['orders']['main']['id']
        
        # Get report
        success, data, status = self.make_request('GET', f'reports/{order_id}')
        self.log_test("Get report", success, f"Status: {status}")

        # Release report (only if order is approved)
        success, data, status = self.make_request('POST', f'reports/{order_id}/release')
        if success:
            self.log_test("Release report", True, f"Report released successfully")
        else:
            self.log_test("Release report", False, f"Status: {status} - {data}")

        return True

    def test_billing(self):
        """Test billing and payment"""
        print("\n💰 Testing Billing & Payments...")
        
        # Get all invoices
        success, data, status = self.make_request('GET', 'invoices')
        if success and len(data) > 0:
            self.test_data['invoices']['all'] = data
            invoice = data[0]
            invoice_id = invoice['id']
            self.log_test("Get all invoices", True, f"Found {len(data)} invoices")
            
            # Get invoice by ID
            success, data, status = self.make_request('GET', f'invoices/{invoice_id}')
            self.log_test("Get invoice by ID", success, f"Status: {status}")
            
            # Record payment
            payment_data = {
                "invoice_id": invoice_id,
                "amount": invoice['net_amount'],
                "payment_mode": "cash",
                "reference": "TEST_PAYMENT_001"
            }
            success, data, status = self.make_request('POST', 'payments', payment_data)
            self.log_test("Record payment", success, f"Status: {status}")
        else:
            self.log_test("Get all invoices", False, f"Status: {status}")

        return True

    def test_analytics(self):
        """Test analytics dashboard"""
        print("\n📊 Testing Analytics...")
        
        success, data, status = self.make_request('GET', 'analytics/dashboard')
        if success:
            stats = data
            self.log_test("Get dashboard analytics", True, 
                         f"Today Orders: {stats.get('today_orders', 0)}, "
                         f"Pending Samples: {stats.get('pending_samples', 0)}, "
                         f"Revenue: ${stats.get('today_revenue', 0)}")
        else:
            self.log_test("Get dashboard analytics", False, f"Status: {status}")

        return True

    def test_settings(self):
        """Test settings and user management"""
        print("\n⚙️ Testing Settings...")
        
        # Get all users (admin only)
        success, data, status = self.make_request('GET', 'users')
        if success and len(data) > 0:
            self.log_test("Get all users", True, f"Found {len(data)} users")
        else:
            self.log_test("Get all users", False, f"Status: {status}")

        return True

    def run_full_workflow_test(self):
        """Test complete end-to-end workflow"""
        print("\n🔄 Testing Complete Workflow...")
        
        workflow_success = True
        
        # 1. Create patient
        patient_data = {
            "name": "Workflow Test Patient",
            "age": 45,
            "gender": "female",
            "phone": "+1987654321",
            "email": "workflow@test.com"
        }
        success, patient, status = self.make_request('POST', 'patients', patient_data)
        if not success:
            self.log_test("Workflow - Create patient", False, f"Status: {status}")
            return False
        
        # 2. Create order
        available_tests = self.test_data['tests']['available']
        order_data = {
            "patient_id": patient['id'],
            "tests": [{
                "test_id": available_tests[0]['id'],
                "test_name": available_tests[0]['name'],
                "test_code": available_tests[0]['code'],
                "price": available_tests[0]['price']
            }],
            "priority": "urgent"
        }
        success, order, status = self.make_request('POST', 'orders', order_data)
        if not success:
            self.log_test("Workflow - Create order", False, f"Status: {status}")
            return False
        
        # 3. Collect sample
        sample_data = {"order_id": order['id'], "sample_type": "blood"}
        success, sample, status = self.make_request('POST', 'samples', sample_data)
        if not success:
            self.log_test("Workflow - Collect sample", False, f"Status: {status}")
            return False
        
        # 4. Enter result (as technician)
        if self.test_data['users'].get('technician'):
            self.token = self.test_data['users']['technician']['access_token']
        
        result_data = {
            "order_id": order['id'],
            "test_id": order['tests'][0]['test_id'],
            "values": {"result": "Normal", "value": "15.2", "unit": "mg/dL"},
            "is_abnormal": False
        }
        success, result, status = self.make_request('POST', 'results', result_data)
        if not success:
            self.log_test("Workflow - Enter result", False, f"Status: {status}")
            return False
        
        # 5. Approve result (as pathologist)
        if self.test_data['users'].get('pathologist'):
            self.token = self.test_data['users']['pathologist']['access_token']
        
        approval_data = {
            "order_id": order['id'],
            "test_id": order['tests'][0]['test_id'],
            "approved": True
        }
        success, approval, status = self.make_request('POST', 'approve', approval_data)
        if not success:
            self.log_test("Workflow - Approve result", False, f"Status: {status}")
            return False
        
        # 6. Release report (as pathologist)
        success, report, status = self.make_request('POST', f'reports/{order["id"]}/release')
        if not success:
            self.log_test("Workflow - Release report", False, f"Status: {status}")
            return False
        
        # Switch back to admin
        if self.test_data['users'].get('admin'):
            self.token = self.test_data['users']['admin']['access_token']
        
        self.log_test("Complete E2E Workflow", True, "Patient → Order → Sample → Result → Approval → Report")
        return True

    def run_all_tests(self):
        """Run all test suites"""
        print("🧪 Starting Laboratory Information System API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        test_functions = [
            self.test_seed_data,
            self.test_authentication,
            self.test_patients,
            self.test_test_catalog,
            self.test_orders,
            self.test_samples,
            self.test_technician_workflow,
            self.test_pathologist_workflow,
            self.test_reports,
            self.test_billing,
            self.test_analytics,
            self.test_settings,
            self.run_full_workflow_test
        ]
        
        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                print(f"❌ Error in {test_func.__name__}: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print(f"✅ Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Print failed tests
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = LISAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())