# A simple Python program to greet the user and calculate the year they will turn 100

# Function to get user input and calculate the year they will turn 100
def greet_user():
    # Ask for user's name
    name = input("Enter your name: ")
    # Ask for user's age
    age = int(input("Enter your age: "))
    
    # Calculate the year the user will turn 100
    current_year = 2023  # You can also use the datetime module to get the current year
    year_100 = current_year + (100 - age)

    # Print a greeting message
    print(f"Hello, {name}! You will turn 100 years old in the year {year_100}.")

# Call the function to execute the program
greet_user()