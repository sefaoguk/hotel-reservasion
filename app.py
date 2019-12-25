import datetime
import moment
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin, user_logged_in, user_logged_out
from flask_login import LoginManager, login_user, logout_user
from sqlalchemy.sql import table, column, select
from sqlalchemy import create_engine, MetaData

class ConfigClass(object):
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///basic_app.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'xyz@gmail.com'
    MAIL_PASSWORD = 'sifre'
    MAIL_DEFAULT_SENDER = '"OtelSekiz" <xyz@gmail.com>'

    USER_APP_NAME = "OtelSekiz"
    USER_ENABLE_EMAIL = True
    USER_ENABLE_USERNAME = False
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = "noreply@example.com"

    USER_ENABLE_CONFIRM_EMAIL = False
    USER_ENABLE_REMEMBER_ME = False

    USER_LOGIN_TEMPLATE = 'giris.html'
    USER_REGISTER_TEMPLATE = 'kayit.html'

    USER_UNAUTHORIZED_ENDPOINT = 'yetki_kontrolu'

def create_app():

    app = Flask(__name__)
    app.config.from_object(__name__+'.ConfigClass')

    login_manager = LoginManager()
    login_manager.init_app(app)
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
       translations = [str(translation) for translation in babel.list_translations()]

    db = SQLAlchemy(app)

    class User(db.Model, UserMixin):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
        email = db.Column(db.String(255, collation='NOCASE'), nullable=False, unique=True)
        email_confirmed_at = db.Column(db.DateTime())
        password = db.Column(db.String(255), nullable=False, server_default='')
        name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
        roles = db.relationship('Role', secondary='user_roles')

    class Role(db.Model):
        __tablename__ = 'roles'
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(50), unique=True)

    class UserRoles(db.Model):
        __tablename__ = 'user_roles'
        id = db.Column(db.Integer(), primary_key=True)
        user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
        role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

    class Oda(db.Model):
        __tablename__ = 'odalar'
        id = db.Column(db.Integer(), primary_key=True)
        baslik = db.Column(db.String(120), server_default='')
        aciklama = db.Column(db.String(200), server_default='')
        fiyat = db.Column(db.String(20), server_default='0')

    class Bonus(db.Model):
        __tablename__ = 'bonuslar'
        id = db.Column(db.Integer(), primary_key=True)
        aciklama = db.Column(db.String(120), server_default='')
        bonus = db.Column(db.String(20), server_default='0')
        musteri = db.Column(db.String(90), server_default='0')
        user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))

    class Rezervasyon(db.Model):
        __tablename__ = 'rezervasyonlar'
        id = db.Column(db.Integer(), primary_key=True)
        giris = db.Column(db.String(30), server_default='')
        cikis = db.Column(db.String(30), server_default='')
        kacgun = db.Column(db.Integer(), server_default='')
        kisi = db.Column(db.Integer(), server_default='')
        oda = db.Column(db.String(30), server_default='')
        fiyat = db.Column(db.Integer(), server_default='')
        musteri = db.Column(db.String(90), server_default='')
        user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))

    class Sepet:
        odalar = {}

    user_manager = UserManager(app, db, User)

    db.create_all()
    engine = create_engine('sqlite:///basic_app.sqlite')
    meta = MetaData(engine).reflect()

    @user_logged_in.connect_via(app)
    def _after_login_hook(sender, user, **extra):
        sender.logger.info('user logged in')

    @user_logged_out.connect_via(app)
    def _after_logout_hook(sender, user, **extra):
        sender.logger.info('user logged out')
        Sepet.odalar = {}

    if not User.query.filter(User.email == 'member@member.com').first():
        user = User(
            name='Üye Member',
            email='member@member.com',
            email_confirmed_at=datetime.utcnow(),
            password=user_manager.hash_password('member123')
        )
        db.session.add(user)
        db.session.commit()

    if not User.query.filter(User.email == 'admin@member.com').first():
        user = User(
            name='Admin Member',
            email='admin@member.com',
            email_confirmed_at=datetime.utcnow(),
            password=user_manager.hash_password('admin123')
        )
        user.roles.append(Role(name='Admin'))
        user.roles.append(Role(name='Agent'))
        db.session.add(user)
        db.session.commit()


    @app.route('/')
    def index():
        return render_template('index.html', bugun = moment.now().format("YYYY-M-D"))

    @app.route('/cikis')
    @login_required
    def logout():
        logout_user()
        Sepet.odalar = {}
        return redirect('/')

    @app.route('/giris', methods = ['GET', 'POST'])
    def giris():
        if current_user.is_authenticated:
            return redirect('/profil')
        if request.method == 'POST':
            mail = request.form['email']
            sifre = request.form['pass']
            user = User.query.filter_by(email=mail).first()
            if not user or not user_manager.verify_password(sifre, user.password):
                return redirect('/giris?h=hata')
            else :
                login_user(user, remember=True)
                next = request.form['next']
                return redirect(next or url_for('profil'))
        return render_template('giris.html')

    @app.route('/kayit', methods = ['GET', 'POST'])
    def kayit():
        if current_user.is_authenticated:
            return redirect('/profil')
        if request.method == 'POST':
            adsoyad = request.form['adsoyad']
            eposta = request.form['mail']
            if request.form['sifre'] != request.form['tsifre']:
                return redirect('/kayit?h=hata')
            sifre = request.form['sifre']
            existing_user = User.query.filter_by(email=eposta).first()
            if existing_user is None:
                user = User(
                    name = adsoyad,
                    email = eposta,
                    email_confirmed_at = datetime.utcnow(),
                    password = user_manager.hash_password(sifre)
                )
                db.session.add(user)
                db.session.commit()
                return redirect('/giris?b=basarili')
            else :
                return redirect('/kayit?h=hata')
        return render_template('admin/kayit.html')

    @app.route('/profil')
    @login_required
    def profil():
        rezervasyonlar = Rezervasyon.query.filter_by(user_id=current_user.id).order_by(Rezervasyon.id).all()
        return render_template('profil.html', rezervasyonlar = rezervasyonlar)

    @app.route('/bonus')
    @login_required
    def bonus():
        bonuslar = Bonus.query.filter_by(user_id=current_user.id).order_by(Bonus.id).all()
        return render_template('bonus.html', bonuslar = bonuslar)

    @app.route('/rezervasyon_kaydet')
    @login_required
    def rezervasyon_kaydet():
        for i in Sepet.odalar:
            kaydet = Rezervasyon(
                giris = Sepet.odalar[i]['giris'],
                cikis = Sepet.odalar[i]['cikis'],
                kacgun = Sepet.odalar[i]['kacgun'],
                oda = Sepet.odalar[i]['oda'],
                fiyat = int(Sepet.odalar[i]['fiyat']),
                kisi = int(Sepet.odalar[i]['kisi']),
                musteri = current_user.name,
                user_id = current_user.id
            )
            bonus_ekle = Bonus(
                aciklama = 'Bonus kazanıldı',
                bonus = int(int(Sepet.odalar[i]['toplam']) * 0.03),
                musteri = current_user.name,
                user_id = current_user.id
            )
            db.session.add(kaydet)
            db.session.add(bonus_ekle)
            db.session.commit()
            Sepet.odalar = {}
        return redirect('/profil?rezervasyon=eklendi')

    @app.route('/sepete_ekle', methods = ['POST'])
    def sepete_ekle():
        if request.method == 'POST':
            giris_tarih = request.form['giris_tarih']
            cikis_tarih = request.form['cikis_tarih']
            kisi_sayisi = request.form['kisi_sayisi']
            kacgun = request.form['kacgun']
            fiyat = request.form['fiyat']
            toplam = request.form['toplam_fiyat']
            oda = request.form['oda']
            key = giris_tarih + '_' + cikis_tarih + '_' + oda
            Sepet.odalar[key] = {
                'giris' : giris_tarih, 'cikis' : cikis_tarih, 'kisi' : kisi_sayisi,
                'kacgun' : kacgun, 'fiyat' : fiyat, 'oda': oda, 'toplam' : toplam
            }
        return redirect('/sepet')

    @app.route('/sepet_sil', methods = ['POST'])
    @login_required
    def sepet_sil():
        if request.method == 'POST':
            sil = request.form['sepet_id'];
            del Sepet.odalar[sil]
        return redirect('/sepet')

    @app.route('/sepet')
    @login_required
    def sepet():
        return render_template('sepet.html', sepetim = Sepet.odalar)

    @app.route('/odalar', methods = ['GET', 'POST'])
    def odalar():
        kacgun = ''
        if request.method == 'POST':
            giris_tarih = request.form['giris_tarih']
            cikis_tarih = request.form['cikis_tarih']
            kacgun = moment.date(cikis_tarih) - moment.date(giris_tarih)
            kacgun = str(kacgun).replace('days, 0:00:00', 'gün').replace('day, 0:00:00', 'gün').replace('0:00:00', '')
            form_bilgi = {
                'giris' : giris_tarih,
                'cikis' : cikis_tarih,
                'kisi' : request.form['kisi']
            }
        odalar = Oda.query.order_by(Oda.id).all()
        return render_template('oteller.html', kacgun = kacgun, form = form_bilgi, odalar = odalar)

    ''' Admin İşlemleri '''
    @app.route('/yetki_kontrolu')
    @login_required
    def yetki_kontrolu():
        return redirect('/profil?yetkisiz=giris')

    @app.route('/admin/odaekle', methods = ['POST'])
    @roles_required('Admin')
    def admin_odaekle():
        if request.method == 'POST':
            oda_adi = request.form['oda_adi']
            oda_fiyat = request.form['oda_fiyat']
            aciklama = request.form['oda_aciklama']
            varmi_oda = Oda.query.filter_by(baslik=oda_adi).first()
            if varmi_oda is None:
                oda = Oda(
                    baslik = oda_adi,
                    aciklama = aciklama,
                    fiyat = int(oda_fiyat)
                )
                db.session.add(oda)
                db.session.commit()
                return redirect('/admin?oda=basarili')
            else :
                oda_guncelle = varmi_oda
                oda_guncelle.fiyat = oda_fiyat
                oda_guncelle.aciklama = aciklama
                db.session.commit()
                return redirect('/admin?oda=guncelleme')
        return redirect('/admin')

    @app.route('/admin')
    @roles_required('Admin')
    def admin_index():
        odalar = Oda.query.order_by(Oda.id).all()
        return render_template('admin/index.html', odalar = odalar)

    @app.route('/admin/rezervasyonlar')
    @roles_required('Admin')
    def admin_rezervasyon():
        rezervasyonlar = Rezervasyon.query.order_by(Rezervasyon.id).all()
        return render_template('admin/rezervasyonlar.html', rezervasyonlar = rezervasyonlar)

    @app.route('/admin/rezervasyon_sil/<id>')
    @roles_required('Admin')
    def admin_rezervasyon_sil(id):
        sil = Rezervasyon.query.filter_by(id=int(id)).first()
        db.session.delete(sil)
        db.session.commit()
        return redirect('/admin/rezervasyonlar')

    @app.route('/admin/oda_sil/<id>')
    @roles_required('Admin')
    def admin_oda_sil(id):
        sil = Oda.query.filter_by(id=int(id)).first()
        db.session.delete(sil)
        db.session.commit()
        return redirect('/admin')

    @app.route('/admin/bonus_sil/<id>')
    @roles_required('Admin')
    def admin_bonus_sil(id):
        sil = Bonus.query.filter_by(id=int(id)).first()
        db.session.delete(sil)
        db.session.commit()
        return redirect('/admin/bonuslar')

    @app.route('/admin/bonuslar')
    @roles_required('Admin')
    def admin_bonuslar():
        bonuslar = Bonus.query.order_by(Bonus.id).all()
        return render_template('admin/bonuslar.html', bonuslar=bonuslar)

    @app.route('/admin/kullanicilar')
    @roles_required('Admin')
    def admin_kullanici():
        kullanicilar = User.query.order_by(User.id).all()
        return render_template('admin/kullanicilar.html', kullanicilar=kullanicilar)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5005)
