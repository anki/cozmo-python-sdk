======================================
Programming Cozmo - Advanced Tutorials
======================================

.. important:: THIS IS THE COZMO SDK BETA. The SDK is under development and is subject to change.

Cozmo is designed for more than just simple move-and-speak programming. Cozmo can be integrated into many other applications through his API.

If you are new to Python, `After Hours Programming <http://www.afterhoursprogramming.com/tutorial/Python/Overview/>`_ and `Codecademy <http://www.codecademy.com/tracks/python>`_ offer beginner's courses in learning Python; `Python.org's website <https://wiki.python.org/moin/BeginnersGuide/NonProgrammers>`_ offers a more comprehensive list of video and web tutorials. This tutorial assumes you have a minimal understanding of programming in general.

-------------------
Twitter Integration
-------------------

The following examples require installation of the `Tweepy <http://www.tweepy.org>`_ Python module - you can do this by typing the following into a Command-Prompt/Terminal window::

    pip3 install --user tweepy

This also requires a Twitter account with developer keys set up specifically for your Cozmo.

To set up a Twitter account with developer keys:

  1. Create a twitter account for your Cozmo and login to that account in your web browser.
  2. Go to `Twitter Application Management <https://apps.twitter.com/app/new>`_ and create your application:

    a. Fill in the name, details, etc. Most of these fields are optional.
    b. Select the **Permissions** tab and set *Access* to *Read and Write*.
    c. Select the **Keys and Access Tokens** tab and click *Generate an Access Token and Secret*.
    d. In your source code editor, open ``cozmo_twitter_keys.py`` and paste your consumer key and secret, and access token and secret into the corresponding **XXXXXXXXXX** fields.

.. important:: Keep the ``cozmo_twitter_keys.py`` file safe - don't distribute it to other people! These keys allow anyone full access to the associated Twitter account!


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Example 1 - Control by Tweet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The code for this example can be found in tweet_at_cozmo.py in the twitter folder of the examples, which can be downloaded from the :doc:`Downloads page</downloads>`.

1. ``twitter_helpers`` is a wrapper that consolidates a list of Tweepy helpers that integrate certain Twitter functions (OAuth authentication, behavior for posting tweets) and define certain scenarios (tweet from user, receiving data that is not a tweet, etc.). Having a Cozmo wrapper like this means that Tweepy does not have to be imported multiple times.
2. ``import cozmo_twitter_keys`` imports the Twitter keys and access tokens required for Cozmo to access his Twitter account.
3. The ``ReactToTweetsStreamListener`` class contains all the different functions that control Cozmo's reactions to tweets sent to @Cozmo'sTwitterHandle.

  a. ``do_drive``

    1. Cozmo drives in a straight line for X number of seconds.
    2. A positive number of seconds drives him forwards; a negative number drives him backwards.
    3. Cozmo will interrupt this action if he detects a cliff or runs into an impassible object such as a wall.

  b. ``do_turn``

    1. Cozmo turns X number of degrees when given this command.
    2. The valid range of degrees is -360 to 0 to 360.

  c. ``do_lift``

    1. Cozmo lifts his forklift.
    2. X is the desired height for the lift; valid range is any number between 0 and 1.

  d. ``do_head``

    1. Cozmo tilts his head up or down.
    2. X is the angle for the head in degrees; valid range is any number between -25 and 44.5.

  e. ``do_say``

    1. Cozmo says the word or phrase tweeted at him.

  f. ``do_photo``

    1. Cozmo uploads a photo of what his camera can currently see.
    2. If Cozmo has no photos or cannot see anything, he will tweet back an error message.

4. The ``on_tweet_from_user`` function defines how Cozmo behaves in regards to retweets and reply posts from his own account, as well as holds information on error handling.

----

`Click here to return to the Cozmo Developer website. <http://developer.anki.com>`_
