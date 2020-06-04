#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(120))
    genres = db.Column(db.String)
    shows = db.relationship('Show', backref='venue', passive_deletes='all', lazy=True)

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String(120))
    genres = db.Column(db.String)
    shows = db.relationship('Show', backref='artist', passive_deletes='all', lazy=True)

class Show(db.Model):
  __tablename__= 'Show'

  id = db.Column(db.Integer, primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id', ondelete='CASCADE'), nullable=False)
  venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id', ondelete='CASCADE'), nullable=False)
  start_time = db.Column(db.DateTime, nullable=False)

# db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  now = datetime.now()
  areas = Venue.query.distinct('city','state').all()
  for area in areas:
    venues = Venue.query.filter(Venue.city == area.city, Venue.state == area.state).all()
    entry = {
      'city': area.city,
      'state': area.state,
      'venues': [{
        'id': venue.id,
        'name': venue.name,
        'num_upcoming_shows': len(Show.query.filter(Show.venue_id == venue.id, Show.start_time > now).all())
        } for venue in venues]
    }
    data.append(entry)

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term=request.form.get('search_term', '')
  # print(search_term)
  data = []
  venues = Venue.query.filter(
    or_(
      Venue.name.ilike('%{}%'.format(search_term)),
      Venue.city.ilike('%{}%'.format(search_term)),
      Venue.state.ilike('%{}%'.format(search_term))
    )
  ).all()
  for venue in venues:
    entry = {
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_show': len(Show.query.filter(Show.venue_id == venue.id).all())
    }
    data.append(entry)

  response={
    "count": len(data),
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  now = datetime.now()
  venue = Venue.query.get(venue_id)
  past_shows = Show.query.filter(Show.venue_id == venue_id, Show.start_time < now).all()
  upcoming_shows = Show.query.filter(Show.venue_id == venue_id, Show.start_time >= now).all()
  genres = venue.genres[1:-1].split(',')
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": [{
      "artist_id": show.artist_id,
      "artist_name": Artist.query.get(show.artist_id).name,
      "artist_image_link": Artist.query.get(show.artist_id).image_link,
      "start_time": format_datetime(str(show.start_time))
    } for show in past_shows ],
    "upcoming_shows": [{
      "artist_id": show.artist_id,
      "artist_name": Artist.query.get(show.artist_id).name,
      "artist_image_link": Artist.query.get(show.artist_id).image_link,
      "start_time": format_datetime(str(show.start_time))
    } for show in upcoming_shows ],
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }
  # print(data)
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm(request.form, meta={"csrf": False})
  if form.validate_on_submit():
    print('form validated')
    try:
      seeking_talent = False
      seeking_description = ''
      if 'seeking_talent' in request.form:
        seeking_talent = form.seeking_talent.data
        if 'seeking_description' in request.form:
          seeking_description = form.seeking_description.data
      artist = Venue(name=form.name.data)
      artist.city = form.city.data
      artist.state = form.state.data
      artist.address = form.address.data
      artist.phone = form.phone.data
      artist.image_link = form.image_link.data
      artist.website = form.website.data
      artist.genres = form.genres.data
      artist.facebook_link = form.facebook_link.data
      artist.seeking_talent = seeking_talent
      artist.seeking_description = seeking_description
      db.session.add(artist)
      db .session.commit()
      flash('Venue ' + artist.name + ' was successfully listed!')
    except SQLAlchemyError as e:
      db.session.rollback()
      print(e)
      flash('An error occurred. Venue ' + artist.name + ' could not be listed.')
    finally:
      db.session.close()
  else:
    print(form.errors)
    flash('An error occurred. Please check the fields and try again', category='error')
    return render_template('forms/new_venue.html', form=VenueForm(request.form, meta={"csrf": False}))

  return render_template('pages/home.html')

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  form = VenueForm(obj=venue)
  data ={
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
  }
  return render_template('forms/edit_venue.html', form=form, venue=data)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm(request.form, meta={"csrf": False})
  if form.validate_on_submit():
    print('form validated')
    try:
      venue = Venue.query.get(venue_id)
      seeking_talent = False
      seeking_description = ''
      if 'seeking_talent' in request.form:
        seeking_talent = form.seeking_talent.data
        if 'seeking_description' in request.form:
          seeking_description = form.seeking_description.data
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.phone = form.phone.data
      venue.image_link = form.image_link.data
      venue.website = form.website.data
      venue.genres = form.genres.data
      venue.facebook_link = form.facebook_link.data
      venue.seeking_talent = seeking_talent
      venue.seeking_description = seeking_description
      db.session.add(venue)
      db.session.commit()
      flash('Venue ' + venue.name + ' was successfully changed.')
    except SQLAlchemyError as e:
      db.session.rollback()
      print(e)
      flash('An error occurred. Changes could not be saved.')
    finally:
      db.session.close()
  else:
    print(form.errors)
    flash('An error occurred. Please check the fields and try again', category='error')
    return render_template('forms/edit_venue.html', form=form, venue=venue)

  return redirect(url_for('show_venue', venue_id=venue_id))

@app.route('/venues/<venue_id>', methods=['POST'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except SQLAlchemyError as e:
    print(e)
    db.session.rollback()
    flash('An error occurred. Venue could not be deleted.')
    return redirect(url_for('/venues'))
  finally:
    db.session.close()
  flash('The venue and shows have been excluded.')
  return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data=[]
  artists = Artist.query.all()
  for artist in artists:
    entry = {
      'id': artist.id,
      'name': artist.name
    }
    data.append(entry)
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term=request.form.get('search_term', '')
  # print(search_term)
  data = []
  artists = Artist.query.filter(
    or_(
      Artist.name.ilike('%{}%'.format(search_term)),
      Artist.city.ilike('%{}%'.format(search_term)),
      Artist.state.ilike('%{}%'.format(search_term))
    )
  ).all()
  for artist in artists:
    entry = {
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_show': len(Show.query.filter(Show.artist_id == artist.id).all())
    }
    data.append(entry)

  response={
    "count": len(data),
    "data": data
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  now = datetime.now()
  artist = Artist.query.get(artist_id)
  past_shows = Show.query.filter(Show.artist_id == artist_id, Show.start_time < now).all()
  upcoming_shows = Show.query.filter(Show.artist_id == artist_id, Show.start_time >= now).all()
  genres = artist.genres[1:-1].split(',')
  # print(type(genres))
  # print(len(genres))
  # print(genres)
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": [{
      "venue_id": show.venue_id,
      "venue_name": Venue.query.get(show.venue_id).name,
      "venue_image_link": Venue.query.get(show.venue_id).image_link,
      "start_time": format_datetime(str(show.start_time))
    } for show in past_shows ],
    "upcoming_shows": [{
      "venue_id": show.venue_id,
      "venue_name": Venue.query.get(show.venue_id).name,
      "venue_image_link": Venue.query.get(show.venue_id).image_link,
      "start_time": format_datetime(str(show.start_time))
    } for show in upcoming_shows ],
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows),
  }
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  form = ArtistForm(obj=artist)
  data ={
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_talent": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }
  return render_template('forms/edit_artist.html', form=form, artist=data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm(request.form, meta={"csrf": False})
  if form.validate_on_submit():
    print('form validated')
    try:
      artist = Artist.query.get(artist_id)
      seeking_venue = False
      seeking_description = ''
      if 'seeking_venue' in request.form:
        seeking_venue = form.seeking_venue.data
        if 'seeking_description' in request.form:
          seeking_description = form.seeking_description.data
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.image_link = form.image_link.data
      artist.website = form.website.data
      artist.genres = form.genres.data
      artist.facebook_link = form.facebook_link.data
      artist.seeking_venue = seeking_venue
      artist.seeking_description = seeking_description
      db.session.add(artist)
      db.session.commit()
      flash('Artist ' + artist.name + ' was successfully changed.')
    except SQLAlchemyError as e:
      db.session.rollback()
      print(e)
      flash('An error occurred. Changes could not be saved.')
    finally:
      db.session.close()
  else:
    print(form.errors)
    flash('An error occurred. Please check the fields and try again', category='error')
    return render_template('forms/edit_artist.html', form=form, artist=artist)

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/artist/<artist_id>', methods=['POST'])
def delete_artist(artist_id):
  try:
    artist = Artist.query.filter_by(id=artist_id).delete()
    db.session.commit()
  except SQLAlchemyError as e:
    print(e)
    db.session.rollback()
    flash('An error occurred. Artist could not be deleted.')
    return redirect(url_for('/artists'))
  finally:
    db.session.close()
  flash('The artist and shows have been excluded.')
  return redirect(url_for('index'))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm(request.form, meta={"csrf": False})
  if form.validate_on_submit():
    print('form validated')
    try:
      seeking_venue = False
      seeking_description = ''
      if 'seeking_venue' in request.form:
        seeking_venue = form.seeking_venue.data
        if 'seeking_description' in request.form:
          seeking_description = form.seeking_description.data
      artist = Artist(name=form.name.data)
      artist.city = form.city.data
      artist.state = form.state.data
      artist.address = form.address.data
      artist.phone = form.phone.data
      artist.image_link = form.image_link.data
      artist.website = form.website.data
      artist.genres = request.form.getlist('genres')
      artist.facebook_link = form.facebook_link.data
      artist.seeking_venue = seeking_venue
      artist.seeking_description = seeking_description
      db.session.add(artist)
      db .session.commit()
      flash('Artist ' + artist.name + ' was successfully listed!')
    except SQLAlchemyError as e:
      db.session.rollback()
      print(e)
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    finally:
      db.session.close()
  else:
    print(form.errors)
    flash('An error occurred. Please check the fields and try again', category='error')
    return render_template('forms/new_artist.html', form=VenueForm(request.form, meta={"csrf": False}))

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data = []
  shows = Show.query.all()
  for show in shows:
    start_time = format_datetime(str(show.start_time))
    entry = {
      'venue_id': show.venue_id,
      'venue_name': show.venue.name,
      'artist_id': show.artist_id,
      'artist_name': show.artist.name,
      'artist_image_link': show.artist.image_link,
      'start_time': start_time
    }
    data.append(entry)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm(request.form, meta={"csrf": False})
  if form.validate_on_submit():
    print('form validated')
    try:
      show = Show()
      show.artist_id = form.artist_id.data
      show.venue_id = form.venue_id.data
      show.start_time = format_datetime(str(form.start_time.data))
      db.session.add(show)
      db.session.commit()
      flash('Show successfully listed!')
    except SQLAlchemyError as e:
      db.session.rollback()
      print(e)
      flash('An error occurred. Show could not be listed.')
    finally:
      db.session.close()
  else:
    print(form.errors)
    flash('An error occurred. Please check the fields and try again', category='error')
    return render_template('forms/new_show.html', form=VenueForm(request.form, meta={"csrf": False}))

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
