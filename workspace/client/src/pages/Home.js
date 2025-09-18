import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import GigCard from '../components/GigCard';
import CategoryCard from '../components/CategoryCard';
import HeroSection from '../components/HeroSection';

const HomeContainer = styled.div`
  min-height: 100vh;
`;

const Section = styled.section`
  padding: 4rem 0;
`;

const SectionTitle = styled.h2`
  text-align: center;
  margin-bottom: 3rem;
  color: ${props => props.theme.secondary};
  font-size: 2.5rem;
`;

const GigGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
`;

const CategoryGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
`;

const StatsSection = styled(Section)`
  background: linear-gradient(135deg, ${props => props.theme.primary}, ${props => props.theme.primaryHover});
  color: white;
  text-align: center;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
`;

const StatItem = styled.div`
  h3 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
  }
  p {
    font-size: 1.2rem;
    opacity: 0.9;
  }
`;

const Home = () => {
  const { data: gigs, isLoading: gigsLoading } = useQuery(
    'featured-gigs',
    () => axios.get('/api/gigs?limit=8&sortBy=rating&sortOrder=desc').then(res => res.data.gigs)
  );

  const { data: topSellers } = useQuery(
    'top-sellers',
    () => axios.get('/api/users/sellers/top?limit=4').then(res => res.data)
  );

  const categories = [
    {
      name: 'Graphics & Design',
      icon: '🎨',
      description: 'Logos, branding, illustrations',
      category: 'graphics-design'
    },
    {
      name: 'Digital Marketing',
      icon: '📈',
      description: 'SEO, social media, ads',
      category: 'digital-marketing'
    },
    {
      name: 'Writing & Translation',
      icon: '✍️',
      description: 'Content, copywriting, translation',
      category: 'writing-translation'
    },
    {
      name: 'Video & Animation',
      icon: '🎬',
      description: 'Video editing, animation, motion',
      category: 'video-animation'
    },
    {
      name: 'Music & Audio',
      icon: '🎵',
      description: 'Voice over, music production',
      category: 'music-audio'
    },
    {
      name: 'Programming',
      icon: '💻',
      description: 'Web development, mobile apps',
      category: 'programming'
    }
  ];

  return (
    <HomeContainer>
      <HeroSection />

      <Section>
        <div className="container">
          <SectionTitle>Popular Categories</SectionTitle>
          <CategoryGrid>
            {categories.map((category) => (
              <CategoryCard key={category.category} category={category} />
            ))}
          </CategoryGrid>
        </div>
      </Section>

      <Section>
        <div className="container">
          <SectionTitle>Featured Gigs</SectionTitle>
          {gigsLoading ? (
            <div className="loading">Loading featured gigs...</div>
          ) : (
            <GigGrid>
              {gigs?.map((gig) => (
                <GigCard key={gig._id} gig={gig} />
              ))}
            </GigGrid>
          )}
          <div style={{ textAlign: 'center', marginTop: '2rem' }}>
            <Link to="/search" className="btn btn-primary">
              View All Gigs
            </Link>
          </div>
        </div>
      </Section>

      <StatsSection>
        <div className="container">
          <SectionTitle>Trusted by Businesses Worldwide</SectionTitle>
          <StatsGrid>
            <StatItem>
              <h3>500K+</h3>
              <p>Freelancers</p>
            </StatItem>
            <StatItem>
              <h3>1M+</h3>
              <p>Happy Clients</p>
            </StatItem>
            <StatItem>
              <h3>50M+</h3>
              <p>Projects Completed</p>
            </StatItem>
            <StatItem>
              <h3>24/7</h3>
              <p>Support Available</p>
            </StatItem>
          </StatsGrid>
        </div>
      </StatsSection>

      <Section>
        <div className="container">
          <SectionTitle>Start Your Journey</SectionTitle>
          <div style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto' }}>
            <p style={{ fontSize: '1.2rem', marginBottom: '2rem', color: '#666' }}>
              Whether you're looking to hire or get hired, our platform connects you with 
              talented freelancers from around the world.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link to="/register" className="btn btn-primary">
                Get Started
              </Link>
              <Link to="/search" className="btn btn-secondary">
                Browse Services
              </Link>
            </div>
          </div>
        </div>
      </Section>
    </HomeContainer>
  );
};

export default Home;