"""
APPLICATION:      BookingChange 1.1
CREATE DATE:      April 14, 2015
MODIFIED DATE:	  April 30, 2015
AUTHOR:           George Friend, for Magnetic Dreams
DESCRIPTION:      When a booking is changed, we get notified and can update the duration field

FUTURE ENHANCEMENTS:
1) somehow impersonate the user who made the change so that it doesn't end up showing ShotgunEvents as the user
2) Notify Don via e-mail when someone changes the schedule
3) Move settings into variables and/or external file
4) Parameterize which users get notificaitons, etc
5) Move all strings for customization and/or internationalization
"""

# IMPORTS
#----------------------------------------------------------------------------------------------------------------------------
from datetime import datetime
import shotgun_api3
from shotgun_api3 import Shotgun
from pprint import pprint # useful for debugging
import logging

# for e-mail notification
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#----------------------------------------------------------------------------------------------------------------------------

# Settings
# TODO Replace the e-mail addresses in the lines below
fromEmail = "fromuser@youremail.com"
toEmail = "touser@youremail.com"
textBodyTemplate = "It would appear that {} has modified the {} field from {} to {} on booking ID {} in the project {}."
htmlBodyTemplate = """\
<html>
  <head></head>
  <body>
    <p><strong>The Scoundrel!</strong></p>
	<p></p>
	<p>
		It would appear that {} has modified the {} field from {} to {} on booking ID {} in the project {}.
	</p>
  </body>
</html>
"""
# End Settings

# EVENT SETUP

def registerCallbacks(reg):
	reg.logger.debug("Registering Callback for BookingChange")
	#TODO put your e-mail address below
	reg.setEmails('yourEmail@email.com')
	eventFilter = {'Shotgun_Booking_Change': ['start_date','end_date']}
	#TODO replace SHOTGUNAPIKEY with your Shotgun API Key below
	reg.registerCallback('ShotgunEvents', 'SHOTGUNAPIKEY', updateDuration, eventFilter, None)
	reg.logger.debug("Registration Complete")

def updateDuration(sg, logger, event, args):
#	logger.debug(str(event))

	if event['entity']:
		id = event['entity']['id']

		fields = ['start_date', 'end_date', 'sg_duration']
		filters = [['id','is',id]]

		result = sg.find_one('Booking',filters,fields)
		if len(result) < 1:
			logger.debug("Could not find booking record: " + id + " - presumably it was deleted?")
    			exit(0)
		else:
			timedelta = datetime.strptime(result['end_date'],'%Y-%m-%d') - datetime.strptime(result['start_date'],'%Y-%m-%d')
			minutes = (timedelta.days + 1) * 8 * 60
			if result['sg_duration'] != minutes:
				sg.update('Booking',result['id'],{ 'sg_duration': minutes })
		
		#In this use case, we only want to send a notification if someone other than John Smith changed the booking since John Smith should making all changes
		#TODO Replace with the username of the person within your organization that should be making updates to bookings
		if event['user']['name'] != 'John Smith':
			sendEmail(event)
			logger.debug(str(event))
			
	else:
		logger.error("Error retrieving event entityID - perhaps it was deleted?")
		logger.debug(str(event))


def sendEmail(event):
	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart('alternative')
	msg['Subject'] = "Booking Change in Shotgun"
	msg['From'] = fromEmail
	msg['To'] = toEmail
	
	# Record the MIME types of both parts - text/plain and text/html.
	
	part1 = MIMEText(textBodyTemplate.format(event['user']['name'],event['meta']['attribute_name'],event['meta']['old_value'],event['meta']['new_value'],event['meta']['entity_id'],event['project']['name']), 'plain')
	part2 = MIMEText(htmlBodyTemplate.format(event['user']['name'],event['meta']['attribute_name'],event['meta']['old_value'],event['meta']['new_value'],event['meta']['entity_id'],event['project']['name']), 'html')
	
	# Attach parts into message container.
	# According to RFC 2046, the last part of a multipart message, in this case
	# the HTML message, is best and preferred.
	msg.attach(part1)
	msg.attach(part2)
	
	# Send the message via local SMTP server.
	#TODO Replace with your mail server below
	s = smtplib.SMTP('mailserver.yourorganization.com')
	# sendmail function takes 3 arguments: sender's address, recipient's address
	# and message to send - here it is sent as one string.
	s.sendmail(fromEmail, toEmail, msg.as_string())
	s.quit()
