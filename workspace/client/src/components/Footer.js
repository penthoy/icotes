import React from 'react';
import styled from 'styled-components';
import { Link } from 'react-router-dom';

const FooterContainer = styled.footer`
  background-color: #fafafa;
  border-top: 1px solid ${props => props.theme.border};
  padding: 3rem 0 2rem;
  margin-top: 4rem;
`;

const FooterContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
`;

const FooterGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
`;

const FooterSection = styled.div`
  h3 {
    color: ${props => props.theme.secondary};
    margin-bottom: 1rem;
    font-size: 1.1rem;
  }
`;

const FooterLink = styled(Link)`
  display: block;
  color: ${props => props.theme.text};
  text-decoration: none;
  margin-bottom: 0.5rem;
  transition: color 0.3s ease;

  &:hover {
    color: ${props => props.theme.primary};
  }
`;

const FooterText = styled.p`
  color: ${props => props.theme.text};
  margin-bottom: 0.5rem;
`;

const FooterBottom = styled.div`
  border-top: 1px solid ${props => props.theme.border};
  padding-top: 2rem;
  text-align: center;
  color: ${props => props.theme.text};
`;

const SocialLinks = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
`;

const SocialLink = styled.a`
  color: ${props => props.theme.text};
  font-size: 1.2rem;
  transition: color 0.3s ease;

  &:hover {
    color: ${props => props.theme.primary};
  }
`;

const Footer = () => {
  return (
    <FooterContainer>
      <FooterContent>
        <FooterGrid>
          <FooterSection>
            <h3>Categories</h3>
            <FooterLink to="/search?category=graphics-design">Graphics & Design</FooterLink>
            <FooterLink to="/search?category=digital-marketing">Digital Marketing</FooterLink>
            <FooterLink to="/search?category=writing-translation">Writing & Translation</FooterLink>
            <FooterLink to="/search?category=video-animation">Video & Animation</FooterLink>
            <FooterLink to="/search?category=music-audio">Music & Audio</FooterLink>
            <FooterLink to="/search?category=programming">Programming & Tech</FooterLink>
          </FooterSection>

          <FooterSection>
            <h3>About</h3>
            <FooterLink to="/about">About Us</FooterLink>
            <FooterLink to="/careers">Careers</FooterLink>
            <FooterLink to="/press">Press & News</FooterLink>
            <FooterLink to="/policies">Policies</FooterLink>
            <FooterLink to="/terms">Terms of Service</FooterLink>
            <FooterLink to="/privacy">Privacy Policy</FooterLink>
          </FooterSection>

          <FooterSection>
            <h3>Support</h3>
            <FooterLink to="/help">Help & Support</FooterLink>
            <FooterLink to="/trust">Trust & Safety</FooterLink>
            <FooterLink to="/community">Community</FooterLink>
            <FooterLink to="/forum">Forum</FooterLink>
            <FooterLink to="/contact">Contact Us</FooterLink>
          </FooterSection>

          <FooterSection>
            <h3>Community</h3>
            <FooterLink to="/events">Events</FooterLink>
            <FooterLink to="/blog">Blog</FooterLink>
            <FooterLink to="/podcast">Podcast</FooterLink>
            <FooterLink to="/invite">Invite a Friend</FooterLink>
            <FooterLink to="/become-seller">Become a Seller</FooterLink>
          </FooterSection>
        </FooterGrid>

        <FooterBottom>
          <FooterText>&copy; 2024 FiverrClone. All rights reserved.</FooterText>
          <FooterText>
            This is a demo project for educational purposes only.
          </FooterText>
          <SocialLinks>
            <SocialLink href="#" aria-label="Facebook">
              📘
            </SocialLink>
            <SocialLink href="#" aria-label="Twitter">
              🐦
            </SocialLink>
            <SocialLink href="#" aria-label="LinkedIn">
              💼
            </SocialLink>
            <SocialLink href="#" aria-label="Instagram">
              📷
            </SocialLink>
          </SocialLinks>
        </FooterBottom>
      </FooterContent>
    </FooterContainer>
  );
};

export default Footer;