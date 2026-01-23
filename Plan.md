# Plan

## User system
    Be able to make a user with a command e.g.
    python main.py createsuperuser --username="{username}" --email="{email}" --password="{password}"

    this command will make a new user will full perms

    ---

    On the website there is an admin panel that is only accessable to superusers
    On the admin panel there will be a users tap where you add a new user
    When you create a new user you will entire Username and Email and it will gen a temp password for the user
    When the user logs in with that temp password they will be forced to set a new passowrd
    the will also be a perm system with these perms
    - Add command
    - Add site
    - Edit command
    - Edit site
    - Delete command
    - Delete site
    - View logs

## Admin Panel
    ### All Tabs
        Users (Manage all users e.g. add/edit/delete users)
        Sites (Be able to add new sites to the dashboard)
        Commands (Be able to add/edit/delete commands for each site)
        Logs (Logs of all proccess on all sites as well as being able to filter for each site and proccses)

## Site system
    When adding a new site you will have these options
    - Site name
    - Base dir
    - Base command (The base command "sudo docker compose exec web python manage.py")

## Command system
    On the command page you will have
    Add/Edit new command
    - Command name
    - Site (Dropdown of all sites)
    - Command string (The actual command to run e.g. "import_bod_avl")
    - Active

    Delete command
    - Confirm deletion

    when a command is started it should check is the only one of that proccess running 
    When a command is stop it should fully kill the service
    if a command dies and it wasnt stopped by an admin is should auto restart and send a notification to a discord webhook

## Logs system
    A system to see live logs of all proccess

## Database
    Defualt should be SQlite but it should have to option to add a pg db in a .env file