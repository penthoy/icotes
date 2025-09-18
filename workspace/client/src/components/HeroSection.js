import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';

const HeroContainer = styled.section`
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4rem 0;
  text-align: center;
`;

const HeroContent = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 0 2rem;
`;

const HeroTitle = styled.h1`
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1rem;
  line-height: 1.2;

  @media (max-width: 768px) {
    font-size: 2rem;
  }
`;

const HeroSubtitle = styled.p`
  font-size: 1.25rem;
  margin-bottom: 2rem;
  opacity: 0.9;
  line-height: 1.6;

  @media (max-width: 768px) {
    font-size: 1.1rem;
  }
`;

const HeroButtons = styled.div`
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
`;

const HeroButton = styled(Link)`
  display: inline-block;
  padding: 1rem 2rem;
  border-radius: 50px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;

  &.primary {
    background: ${props => props.theme.primary};
    color: white;

    &:hover {
      background: ${props => props.theme.primaryHover};
      transform: translateY(-2px);
    }
  }

  &.secondary {
    background: transparent;
    color: white;
    border: 2px solid white;

    &:hover {
      background: white;
      color: ${props => props.theme.primary};
    }
  }
`;

const HeroSection = () => {
  return (
    <HeroContainer>
      <HeroContent>
        <HeroTitle>
          Find the perfect freelance services for your business
        </HeroTitle>
        <HeroSubtitle>
          Connect with talented freelancers from around the world. 
          Get quality work done faster and more efficiently.
        </HeroSubtitle>
        <HeroButtons>
          <HeroButton to="/search" className="primary">
            Find Services
          </HeroButton>
          <HeroButton to="/register" className="secondary">
            Become a Seller
          </HeroButton>
        </HeroButtons>
      </HeroContent>
    </HeroContainer>
  );
};

export default HeroSection;