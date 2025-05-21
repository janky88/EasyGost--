from app import db
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Servers(db.Model):
    __tablename__ = 'servers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=False, unique=True) # IPv4 or IPv6
    ssh_username = db.Column(db.String(100), nullable=False)
    ssh_password = db.Column(db.String(255), nullable=False) # Will be encrypted
    ssh_port = db.Column(db.Integer, nullable=False, default=22)
    connection_status = db.Column(db.String(50), default='pending') # e.g., pending, connected, disconnected, error
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Transits where this server is server_a
    transits_a = relationship("Transits", foreign_keys="Transits.server_a_id", back_populates="server_a", lazy=True)
    # Transits where this server is server_b
    transits_b = relationship("Transits", foreign_keys="Transits.server_b_id", back_populates="server_b", lazy=True)

    def __repr__(self):
        return f'<Server {self.name}>'

class Transits(db.Model):
    __tablename__ = 'transits'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    server_a_id = db.Column(db.Integer, ForeignKey('servers.id'), nullable=False)
    server_a_listen_port = db.Column(db.Integer, nullable=False)
    
    server_b_id = db.Column(db.Integer, ForeignKey('servers.id'), nullable=False)
    server_b_connect_port = db.Column(db.Integer, nullable=False) # Port on Server B that Server A's transit connects to
    
    encryption_protocol = db.Column(db.String(50), default='ssh') # e.g., ssh, wireguard, openvpn
    destination_ip = db.Column(db.String(45), nullable=False) # The final destination IP the user wants to reach through server B
    destination_port = db.Column(db.Integer, nullable=False) # The final destination port
    
    status = db.Column(db.String(50), default='pending') # e.g., pending, active, inactive, error
    latency_ms = db.Column(db.Float, nullable=True) # Latency in milliseconds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    server_a = relationship("Servers", foreign_keys=[server_a_id], back_populates="transits_a")
    server_b = relationship("Servers", foreign_keys=[server_b_id], back_populates="transits_b")

    def __repr__(self):
        return f'<Transit {self.name}>'
