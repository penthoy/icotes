import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import styled from 'styled-components';
import { FiStar, FiMapPin, FiUser, FiMail, FiCalendar } from 'react-icons/fi';
import GigCard from '../components/GigCard';

const ProfileContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const ProfileHeader = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 2rem;
  align-items: center;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    text-align: center;
  }
`;

const ProfileAvatar = styled.img`
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
`;

const ProfileInfo = styled.div`
  h1 {
    color: ${props => props.theme.secondary};
    margin-bottom: 0.5rem;
  }
`;

const ProfileStats = styled.div`
  display: flex;
  gap: 2rem;
  margin: 1rem 0;
`;

const StatItem = styled.div`
  text-align: center;
  
  h3 {
    color: ${props => props.theme.primary};
    margin-bottom: 0.25rem;
  }
  
  p {
    color: ${props => props.theme.text};
    font-size: 0.9rem;
  }
`;

const ProfileDetails = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  color: ${props => props.theme.text};
  margin-bottom: 0.5rem;
`;

const ProfileContent = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const ProfileSidebar = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: fit-content;
`;

const SectionTitle = styled.h2`
  color: ${props => props.theme.secondary};
  margin-bottom: 1rem;
`;

const GigGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
`;

const SkillsList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
`;

const SkillTag = styled.span`
  background: ${props => props.theme.primary};
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.9rem;
`;

const Profile = () => {
  const { id } = useParams();
  const { user: currentUser } = useAuth();
  
  // If no ID provided, show current user's profile
  const userId = id || currentUser?.id;

  const { data: user, isLoading: userLoading } = useQuery(
    ['user', userId],
    () => axios.get(`/api/users/${userId}`).then(res => res.data),
    { enabled: !!userId }
  );

  const { data: gigs, isLoading: gigsLoading } = useQuery(
    ['user-gigs', userId],
    () => axios.get(`/api/gigs/user/${userId}`).then(res => res.data),
    { enabled: !!userId }
  );

  if (userLoading) return <div className="loading">Loading profile...</div>;
  if (!user) return <div className="error">User not found</div>;

  const isOwnProfile = currentUser?.id === user._id;

  return (
    <ProfileContainer>
      <ProfileHeader>
        {user.profilePicture ? (
          <ProfileAvatar src={user.profilePicture} alt={user.username} />
        ) : (
          <div style={{ 
            width: 120, 
            height: 120, 
            borderRadius: '50%', 
            background: '#ddd',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '48px',
            color: '#666'
          }}>
            {user.username?.charAt(0)?.toUpperCase() || 'U'}
          </div>
        )}
        
        <ProfileInfo>
          <h1>{user.username}</h1>
          <ProfileDetails>
            <FiMapPin /> {user.country}
          </ProfileDetails>
          <ProfileDetails>
            <FiCalendar /> Member since {new Date(user.memberSince).toLocaleDateString()}
          </ProfileDetails>
          
          {user.isSeller && (
            <ProfileStats>
              <StatItem>
                <h3>{user.rating.toFixed(1)}</h3>
                <p>Average Rating</p>
              </StatItem>
              <StatItem>
                <h3>{user.totalReviews}</h3>
                <p>Reviews</p>
              </StatItem>
              <StatItem>
                <h3>${user.earnings}</h3>
                <p>Earnings</p>
              </StatItem>
            </ProfileStats>
          )}
        </ProfileInfo>
      </ProfileHeader>

      <ProfileContent>
        <ProfileSidebar>
          <SectionTitle>About</SectionTitle>
          <p style={{ color: '#666', marginBottom: '1.5rem' }}>
            {user.description || 'No description provided.'}
          </p>

          {user.isSeller && user.skills && user.skills.length > 0 && (
            <>
              <SectionTitle>Skills</SectionTitle>
              <SkillsList>
                {user.skills.map((skill, index) => (
                  <SkillTag key={index}>{skill}</SkillTag>
                ))}
              </SkillsList>
            </>
          )}

          {user.languages && user.languages.length > 0 && (
            <>
              <SectionTitle style={{ marginTop: '1.5rem' }}>Languages</SectionTitle>
              <div>
                {user.languages.map((lang, index) => (
                  <div key={index} style={{ color: '#666', marginBottom: '0.5rem' }}>
                    {lang.language} - {lang.level}
                  </div>
                ))}
              </div>
            </>
          )}
        </ProfileSidebar>

        <div>
          {user.isSeller && (
            <>
              <SectionTitle>Services</SectionTitle>
              {gigsLoading ? (
                <div className="loading">Loading services...</div>
              ) : gigs?.length > 0 ? (
                <GigGrid>
                  {gigs.map(gig => (
                    <GigCard key={gig._id} gig={gig} />
                  ))}
                </GigGrid>
              ) : (
                <p style={{ color: '#666', textAlign: 'center' }}>
                  {isOwnProfile ? 'You haven\'t created any gigs yet.' : 'This seller hasn\'t created any gigs yet.'}
                </p>
              )}
            </>
          )}

          {!user.isSeller && (
            <div style={{ textAlign: 'center', padding: '3rem' }}>
              <h3 style={{ color: '#666', marginBottom: '1rem' }}>
                {user.username} is not currently offering services
              </h3>
              {isOwnProfile && (
                <button className="btn btn-primary">
                  Become a Seller
                </button>
              )}
            </div>
          )}
        </div>
      </ProfileContent>
    </ProfileContainer>
  );
};

export default Profile;