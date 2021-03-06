from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from datetime import datetime

from django.http import HttpResponse

#Import the category model
from rango.models import Category
#Import the page model
from rango.models import Page



def show_category(request, category_name_slug):
    # Create a context dictionary which we can pass
    # to the template rendering engine
    context_dict = {}

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExisst exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)

        # Retrieve all of the associated pages.
        # Note that filter() will return a list of page objects or an empty list
        pages = Page.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages

        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category

    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything -
        # the template will display the "no category" message for us.
        context_dict['category'] = None
        context_dict['pages'] = None

    return render(request, 'rango/category.html', context_dict)

@login_required
def add_category(request):
    form = CategoryForm()

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            #Save the new category to the database
            form.save(commit=True)
            # Now that the category is saved
            # We could give a confirmation message
            # But since the most recent category added is on the index page
            # Then we can direct the user back to the index page
            return index(request)
        else:

            # The supplied form contained errors -
            # Just print them to the terminal
            print(form.errors)
    # Will handle the bad form, new form or no form supplied cases
    # Render the form with error messages (if any)
    return render(request, 'rango/add_category.html',{'form':form})

@login_required
def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    form = PageForm()
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()
                return show_category(request,category_name_slug)
        else:
            print(form.errors)

    context_dict = {'form':form, 'category': category}
    return render(request, 'rango/add_page.html', context_dict)

def user_login(request):

    # If HTTP POST, pull out form data and process it.
    if request.method == 'POST':
        # Gather username and password provided by user
        # This information is obtained from the login form
        # We use request.POST.get('<variable>') as opposed to request.POST['<variable>'] because
        # the request.POST.get('<variable>') returns None if the value does not exist
        # while request.POST['<variable>'] will raise a keyError exception
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Attempt to log the user in with the supplied credentials.
        # A User object is returned if correct - None if not.
        user = authenticate(username=username, password=password)

        # A valid user logged in?
        if user:
            # Check if the account is active (can be used).
            # If so, log the user in and redirect them to the homepage.
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse('index'))
            # The account is inactive; tell by adding variable to the template context.
            else:
                return HttpResponse("Your rango account is disabled")
        # Invalid login details supplied!
        else:
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied.")

    # Not a HTTP POST - most likely a HTTP GET. In this case, we render the login form for the user.
    else:
        return render(request, 'rango/login.html', {})



def index(request):
    #Set test cookie
    request.session.set_test_cookie()
    # Query the database for a list of ALL categories currently stored.
    # Order the categories by no. likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the list in our context_dict dictionary
    # that will be passed to the template engine.

    category_list = Category.objects.order_by('-likes')[:5]
    pages_list = Page.objects.order_by('-views')[:5]

    # Construct a dictionary to pass to the template engine as it's context.
    context_dict = {'categories':category_list, 'pages':pages_list}

    #Call function to handle the cookies
    visitor_cookie_handler(request)

    context_dict['visits'] = request.session['visits']

    #Obtain our Response object early so we can add cookie information

    response = render(request, 'rango/index.html', context_dict)
    return response


def about(request):
    context_dict = {}
    if request.session.test_cookie_worked():
        print("TEST COOKIE WORKED")
        request.session.delete_test_cookie()
    # prints out whether the method is a GET or a POST
    print(request.method)
    # prints out the user name, if no one is logged in it prints 'AnonymousUser'
    print(request.user)

    visitor_cookie_handler(request)

    context_dict['visits'] = request.session['visits']

    response = render(request, 'rango/about.html', context_dict)

    return response


def register(request):
    # A boolean value for the telling the template
    # whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds

    registered= False

    # If it's a HTTP POST, we're interested in processing the form data
    if request.method == 'POST':
        # Attempt to grab information frmo the raw form information
        # Note that we make use of both UserForm and UserProfileForm
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        #If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database
            user = user_form.save()
            # Now we hash the password with the set_password method
            # Once hashed, we can update the user object
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance
            # Since we need to set the user attribute ourselves,
            # we set commit=False. This delays saving the model
            # until we're ready to avoid integrity problems
            profile = profile_form.save(commit=False)
            profile.user = user

            #Did the user provide a profile picture?
            #If so, we need to get it from the input form and put it in the UserProfile model
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

                # Now we save the UserProfile model instance
                profile.save()

                # Update our variable to indicate that the template registration was successful
                registered = True
        else:
            # Invalid form or forms - mistakes or something else?
            # Print problems to the terminal
            print(user_form.errors,profile_form.errors)
    else:
        # Not a HTTP post, so we render our form using two ModelForm instances
        # These forms will be blank, ready for user input
        user_form = UserForm()
        profile_form = UserProfileForm()

    #Render the template depending on the context
    return render(request,'rango/register.html',
                      {'user_form':user_form,
                       'profile_form':profile_form,
                       'registered':registered})


@login_required
def restricted(request):
    return render(request, 'rango/restricted.html', {})

def user_logout(request):
    # Since we know the user is logged in, we can now just log them out
    logout(request)
    #Take the user back to the homepage
    return HttpResponseRedirect(reverse('index'))

def get_server_side_cookie(request,cookie,default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val

def visitor_cookie_handler(request):
    # Get the number of visits to the site.
    # We use the COOKIES.get() function to obtain the visits cookie.
    # If the cookie exists, the value returned is casted to an integer.
    # If the cookie doesn't exist, then the default value of 1 is used.
    visits = int(request.COOKIES.get('visits', '1'))

    last_visit_cookie = request.COOKIES.get('last_visit', str(datetime.now()))

    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')
    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        visits = 1
        # set the last visit cookie
        request.session['last_visit'] = str(datetime.now())
    # Update/set the visits cookie
    request.session['visits'] = visits
























