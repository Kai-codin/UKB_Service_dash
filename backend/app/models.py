from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    base_path = Column(String)
    base_command = Column(String, nullable=True)
    commands = relationship("Command", back_populates="site")


class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    name = Column(String)
    command_template = Column(Text)
    current_pid = Column(Integer, nullable=True)
    site = relationship("Site", back_populates="commands")
    envs = relationship("Env", back_populates="command", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="command", cascade="all, delete-orphan")


class Env(Base):
    __tablename__ = "envs"
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("commands.id"))
    key = Column(String)
    value = Column(String)
    command = relationship("Command", back_populates="envs")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    perms = Column(String, default="")
    token = Column(String, nullable=True, index=True)


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("commands.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    output_path = Column(String)
    status = Column(String, default="running")
    command = relationship("Command", back_populates="logs")
