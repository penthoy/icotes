import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';

const CreateGigContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
`;

const Title = styled.h1`
  color: ${props => props.theme.secondary};
  margin-bottom: 2rem;
`;

const FormSection = styled.div`
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
`;

const SectionTitle = styled.h2`
  color: ${props => props.theme.secondary};
  margin-bottom: 1rem;
  font-size: 1.5rem;
`;

const FormGroup = styled.div`
  margin-bottom: 1.5rem;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: ${props => props.theme.secondary};
`;

const Input = styled.input`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid ${props => props.theme.border};
  border-radius: 4px;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: ${props => props.theme.primary};
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid ${props => props.theme.border};
  border-radius: 4px;
  font-size: 1rem;
  min-height: 100px;
  resize: vertical;

  &:focus {
    outline: none;
    border-color: ${props => props.theme.primary};
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid ${props => props.theme.border};
  border-radius: 4px;
  font-size: 1rem;

  &:focus {
    outline: none;
    border-color: ${props => props.theme.primary};
  }
`;

const PackageGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const PackageCard = styled.div`
  border: 1px solid ${props => props.theme.border};
  border-radius: 8px;
  padding: 1.5rem;
`;

const PackageTitle = styled.h3`
  color: ${props => props.theme.secondary};
  margin-bottom: 1rem;
`;

const Button = styled.button`
  padding: 1rem 2rem;
  background: ${props => props.theme.primary};
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;

  &:hover {
    background: ${props => props.theme.primaryHover};
  }
`;

const CreateGig = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    subCategory: '',
    tags: '',
    pricing: {
      basic: { name: 'Basic', description: '', deliveryTime: 3, revisions: 1, price: 5, features: [] },
      standard: { name: 'Standard', description: '', deliveryTime: 5, revisions: 2, price: 15, features: [] },
      premium: { name: 'Premium', description: '', deliveryTime: 7, revisions: 3, price: 30, features: [] }
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    // In a real app, this would make an API call
    alert('Gig created successfully! (This is a demo)');
    navigate('/');
  };

  return (
    <CreateGigContainer>
      <Title>Create a New Gig</Title>
      
      <form onSubmit={handleSubmit}>
        <FormSection>
          <SectionTitle>Gig Overview</SectionTitle>
          
          <FormGroup>
            <Label>Gig Title</Label>
            <Input
              type="text"
              placeholder="e.g., I will design a professional logo for your business"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              maxLength="100"
              required
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Category</Label>
            <Select
              value={formData.category}
              onChange={(e) => setFormData({...formData, category: e.target.value})}
              required
            >
              <option value="">Select a category</option>
              <option value="graphics-design">Graphics & Design</option>
              <option value="digital-marketing">Digital Marketing</option>
              <option value="writing-translation">Writing & Translation</option>
              <option value="video-animation">Video & Animation</option>
              <option value="music-audio">Music & Audio</option>
              <option value="programming">Programming & Tech</option>
            </Select>
          </FormGroup>
          
          <FormGroup>
            <Label>Description</Label>
            <TextArea
              placeholder="Describe your service in detail..."
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              maxLength="1000"
              required
            />
          </FormGroup>
          
          <FormGroup>
            <Label>Tags (comma separated)</Label>
            <Input
              type="text"
              placeholder="e.g., logo, branding, design"
              value={formData.tags}
              onChange={(e) => setFormData({...formData, tags: e.target.value})}
            />
          </FormGroup>
        </FormSection>

        <FormSection>
          <SectionTitle>Pricing Packages</SectionTitle>
          <PackageGrid>
            {Object.entries(formData.pricing).map(([key, packageData]) => (
              <PackageCard key={key}>
                <PackageTitle>{packageData.name}</PackageTitle>
                <FormGroup>
                  <Label>Description</Label>
                  <TextArea
                    value={packageData.description}
                    onChange={(e) => setFormData({
                      ...formData,
                      pricing: {
                        ...formData.pricing,
                        [key]: { ...packageData, description: e.target.value }
                      }
                    })}
                    placeholder="What's included in this package?"
                  />
                </FormGroup>
                <FormGroup>
                  <Label>Delivery Time (days)</Label>
                  <Input
                    type="number"
                    min="1"
                    max="30"
                    value={packageData.deliveryTime}
                    onChange={(e) => setFormData({
                      ...formData,
                      pricing: {
                        ...formData.pricing,
                        [key]: { ...packageData, deliveryTime: parseInt(e.target.value) }
                      }
                    })}
                  />
                </FormGroup>
                <FormGroup>
                  <Label>Revisions</Label>
                  <Input
                    type="number"
                    min="0"
                    max="10"
                    value={packageData.revisions}
                    onChange={(e) => setFormData({
                      ...formData,
                      pricing: {
                        ...formData.pricing,
                        [key]: { ...packageData, revisions: parseInt(e.target.value) }
                      }
                    })}
                  />
                </FormGroup>
                <FormGroup>
                  <Label>Price ($)</Label>
                  <Input
                    type="number"
                    min="5"
                    max="10000"
                    value={packageData.price}
                    onChange={(e) => setFormData({
                      ...formData,
                      pricing: {
                        ...formData.pricing,
                        [key]: { ...packageData, price: parseInt(e.target.value) }
                      }
                    })}
                  />
                </FormGroup>
              </PackageCard>
            ))}
          </PackageGrid>
        </FormSection>

        <Button type="submit">Create Gig</Button>
      </form>
    </CreateGigContainer>
  );
};

export default CreateGig;