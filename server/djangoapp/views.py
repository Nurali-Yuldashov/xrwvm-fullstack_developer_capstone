# Uncomment the required imports before adding the code

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from datetime import datetime
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from .restapis import get_request, analyze_review_sentiments, post_review
from .populate import initiate
from .models import CarMake, CarModel


# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your views here.

# Create a `login_request` view to handle sign in request
@csrf_exempt
def login_user(request):
    # Get username and password from request.POST dictionary
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    # Try to check if provide credential can be authenticated
    user = authenticate(username=username, password=password)
    data = {"userName": username}
    if user is not None:
        # If user is valid, call login method to login current user
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
    return JsonResponse(data)

# Create a `logout_request` view to handle sign out request
# In djangoapp/views.py
def logout_request(request):
    logout(request)
    data = {"userName":""}
    return JsonResponse(data)

# Create a `registration` view to handle sign up request
@csrf_exempt
def registration(request):
    context = {}

    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    first_name = data['firstName']
    last_name = data['lastName']
    email = data['email']
    username_exist = False
    email_exist = False
    try:
        # Check if user already exists
        User.objects.get(username=username)
        username_exist = True
    except:
        # If not, simply log this is a new user
        logger.debug("{} is new user".format(username))

    # If it is a new user
    if not username_exist:
        # Create user in auth_user table
        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,password=password, email=email)
        # Login the user and redirect to list page
        login(request, user)
        data = {"userName":username,"status":"Authenticated"}
        return JsonResponse(data)
    else :
        data = {"userName":username,"error":"Already Registered"}
        return JsonResponse(data)

#Update the `get_dealerships` render list of dealerships all by default, particular state if state is passed
def get_dealerships(request, state="All"):
    if(state == "All"):
        endpoint = "/fetchDealers"
    else:
        endpoint = "/fetchDealers/"+state
    dealerships = get_request(endpoint)
    return JsonResponse({"status":200,"dealers":dealerships})

# Create a `get_dealer_reviews` view to render the reviews of a dealer
# def get_dealer_reviews(request,dealer_id):
def get_dealer_reviews(request, dealer_id):
    """
    Retrieve reviews for a specific dealer
    Parameters:
        - dealer_id: The ID of the dealer
    Returns:
        - JsonResponse containing dealer reviews
    """
    try:
        # Get reviews from the backend API
        reviews = get_request(f"dealers/{dealer_id}/reviews")
        
        if reviews:
            # Process and format the reviews
            formatted_reviews = []
            for review in reviews:
                formatted_review = {
                    "id": review.get("id"),
                    "reviewer": review.get("name", "Anonymous"),
                    "dealership": dealer_id,
                    "review": review.get("review", ""),
                    "purchase": review.get("purchase", False),
                    "purchase_date": review.get("purchase_date", ""),
                    "car_make": review.get("car_make", ""),
                    "car_model": review.get("car_model", ""),
                    "car_year": review.get("car_year", ""),
                    "rating": review.get("rating", 0)
                }
                formatted_reviews.append(formatted_review)
                
            return JsonResponse({"reviews": formatted_reviews})
        else:
            return JsonResponse({"error": "No reviews found"}, status=404)
            
    except Exception as e:
        print(f"Error getting dealer reviews: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

# Create a `get_dealer_details` view to render the dealer details
# def get_dealer_details(request, dealer_id):
def get_dealer_details(request, dealer_id):
    """
    Retrieve details for a specific dealer
    Parameters:
        - dealer_id: The ID of the dealer
    Returns:
        - JsonResponse containing dealer details
    """
    try:
        # Call the get_request from restapis.py to get dealer details
        url = f"https://api.example.com/api/dealers/{dealer_id}"  # Replace with your actual API endpoint
        dealer_details = get_request(f"dealers/{dealer_id}")
        
        if dealer_details:
            dealer_data = {
                "id": dealer_id,
                "name": dealer_details.get("full_name", ""),
                "address": dealer_details.get("address", ""),
                "city": dealer_details.get("city", ""),
                "state": dealer_details.get("state", ""),
                "zip": dealer_details.get("zip", ""),
                "phone": dealer_details.get("phone", ""),
                "email": dealer_details.get("email", "")
            }
            return JsonResponse({"dealer": dealer_data})
        else:
            return JsonResponse({"error": "Dealer not found"}, status=404)
            
    except Exception as e:
        print(f"Error getting dealer details: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

# Create a `add_review` view to submit a review
# def add_review(request):
@csrf_exempt
def add_review(request):
    """
    Add a review for a specific dealer
    """
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            review_data = json.loads(request.body)
            
            # Extract review data
            dealer_id = review_data.get('dealer_id')
            review = review_data.get('review')
            purchase = review_data.get('purchase', False)
            purchase_date = review_data.get('purchase_date', '')
            car_make = review_data.get('car_make', '')
            car_model = review_data.get('car_model', '')
            car_year = review_data.get('car_year', '')
            rating = review_data.get('rating', 0)
            
            # Validate required fields
            if not all([dealer_id, review, rating]):
                return JsonResponse({
                    "error": "Missing required fields"
                }, status=400)
            
            # Create review data structure
            new_review = {
                "dealer_id": dealer_id,
                "review": review,
                "purchase": purchase,
                "purchase_date": purchase_date,
                "car_make": car_make,
                "car_model": car_model,
                "car_year": car_year,
                "rating": rating
            }
            
            # Send the review to your backend API
            response = post_request('reviews/dealer/' + str(dealer_id), new_review)
            
            if response:
                return JsonResponse({"message": "Review added successfully"})
            else:
                return JsonResponse({"error": "Failed to add review"}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)

logger = logging.getLogger(__name__)

def get_cars(request):
    try:
        # Clear existing data
        print("Cleaning existing data...")
        CarModel.objects.all().delete()
        CarMake.objects.all().delete()
        
        print("Creating new car makes...")
        # Create car makes
        car_makes = {
            'NISSAN': CarMake.objects.create(name="NISSAN", description="Great cars. Japanese technology"),
            'Mercedes': CarMake.objects.create(name="Mercedes", description="Great cars. German technology"),
            'Audi': CarMake.objects.create(name="Audi", description="Great cars. German technology"),
            'Kia': CarMake.objects.create(name="Kia", description="Great cars. Korean technology"),
            'Toyota': CarMake.objects.create(name="Toyota", description="Great cars. Japanese technology")
        }
        
        print(f"Created {len(car_makes)} car makes")

        # Create car models with explicit error handling
        car_models_data = [
            {"name": "Pathfinder", "type": "SUV", "year": 2023, "car_make": car_makes['NISSAN'], "dealer_id": 1},
            {"name": "Qashqai", "type": "SUV", "year": 2023, "car_make": car_makes['NISSAN'], "dealer_id": 1},
            {"name": "XTRAIL", "type": "SUV", "year": 2023, "car_make": car_makes['NISSAN'], "dealer_id": 1},
            {"name": "A-Class", "type": "SUV", "year": 2023, "car_make": car_makes['Mercedes'], "dealer_id": 1},
            {"name": "C-Class", "type": "SUV", "year": 2023, "car_make": car_makes['Mercedes'], "dealer_id": 1},
            {"name": "E-Class", "type": "SUV", "year": 2023, "car_make": car_makes['Mercedes'], "dealer_id": 1},
            {"name": "A4", "type": "SUV", "year": 2023, "car_make": car_makes['Audi'], "dealer_id": 1},
            {"name": "A5", "type": "SUV", "year": 2023, "car_make": car_makes['Audi'], "dealer_id": 1},
            {"name": "A6", "type": "SUV", "year": 2023, "car_make": car_makes['Audi'], "dealer_id": 1},
            {"name": "Sorrento", "type": "SUV", "year": 2023, "car_make": car_makes['Kia'], "dealer_id": 1},
            {"name": "Carnival", "type": "SUV", "year": 2023, "car_make": car_makes['Kia'], "dealer_id": 1},
            {"name": "Cerato", "type": "Sedan", "year": 2023, "car_make": car_makes['Kia'], "dealer_id": 1},
            {"name": "Corolla", "type": "Sedan", "year": 2023, "car_make": car_makes['Toyota'], "dealer_id": 1},
            {"name": "Camry", "type": "Sedan", "year": 2023, "car_make": car_makes['Toyota'], "dealer_id": 1},
            {"name": "Kluger", "type": "SUV", "year": 2023, "car_make": car_makes['Toyota'], "dealer_id": 1}
        ]

        print("Creating car models...")
        for model_data in car_models_data:
            try:
                car_model = CarModel.objects.create(**model_data)
                print(f"Successfully created car model: {model_data['name']}")
            except Exception as e:
                print(f"Error creating car model {model_data['name']}: {str(e)}")

        # Fetch all car models with their makes
        car_models = CarModel.objects.select_related('car_make').all()
        cars = []
        for car_model in car_models:
            cars.append({
                "CarModel": car_model.name,
                "CarMake": car_model.car_make.name,
                "Type": car_model.type,
                "Year": car_model.year
            })
        
        print(f"Returning {len(cars)} cars")
        return JsonResponse({"CarModels": cars})

    except Exception as e:
        print(f"Error in get_cars: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)