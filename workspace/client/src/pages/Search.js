import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import axios from 'axios';
import styled from 'styled-components';
import GigCard from '../components/GigCard';

const SearchContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const SearchHeader = styled.div`
  margin-bottom: 2rem;
`;

const SearchTitle = styled.h1`
  color: ${props => props.theme.secondary};
  margin-bottom: 0.5rem;
`;

const SearchResults = styled.p`
  color: ${props => props.theme.text};
`;

const SearchContent = styled.div`
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 2rem;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const Filters = styled.div`
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: fit-content;
  position: sticky;
  top: 100px;
`;

const FilterGroup = styled.div`
  margin-bottom: 1.5rem;
`;

const FilterTitle = styled.h3`
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: ${props => props.theme.secondary};
`;

const FilterInput = styled.input`
  width: 100%;
  padding: 0.5rem;
  border: 1px solid ${props => props.theme.border};
  border-radius: 4px;
  margin-bottom: 0.5rem;
`;

const FilterSelect = styled.select`
  width: 100%;
  padding: 0.5rem;
  border: 1px solid ${props => props.theme.border};
  border-radius: 4px;
  margin-bottom: 0.5rem;
`;

const FilterCheckbox = styled.input`
  margin-right: 0.5rem;
`;

const FilterLabel = styled.label`
  display: block;
  margin-bottom: 0.25rem;
  color: ${props => props.theme.text};
  font-size: 0.9rem;
`;

const GigGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
`;

const Pagination = styled.div`
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 2rem;
`;

const PageButton = styled.button`
  padding: 0.5rem 1rem;
  border: 1px solid ${props => props.theme.border};
  background: white;
  color: ${props => props.theme.text};
  border-radius: 4px;
  cursor: pointer;

  &:hover {
    background: ${props => props.theme.primary};
    color: white;
  }

  &.active {
    background: ${props => props.theme.primary};
    color: white;
  }

  &:disabled {
    background: #f5f5f5;
    color: #ccc;
    cursor: not-allowed;
  }
`;

const categories = [
  { value: '', label: 'All Categories' },
  { value: 'graphics-design', label: 'Graphics & Design' },
  { value: 'digital-marketing', label: 'Digital Marketing' },
  { value: 'writing-translation', label: 'Writing & Translation' },
  { value: 'video-animation', label: 'Video & Animation' },
  { value: 'music-audio', label: 'Music & Audio' },
  { value: 'programming', label: 'Programming & Tech' },
  { value: 'business', label: 'Business' },
  { value: 'lifestyle', label: 'Lifestyle' }
];

const sortOptions = [
  { value: 'createdAt-desc', label: 'Newest' },
  { value: 'createdAt-asc', label: 'Oldest' },
  { value: 'rating-desc', label: 'Best Rating' },
  { value: 'pricing.basic.price-asc', label: 'Price: Low to High' },
  { value: 'pricing.basic.price-desc', label: 'Price: High to Low' }
];

const Search = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState({
    q: searchParams.get('q') || '',
    category: searchParams.get('category') || '',
    minPrice: searchParams.get('minPrice') || '',
    maxPrice: searchParams.get('maxPrice') || '',
    deliveryTime: searchParams.get('deliveryTime') || '',
    sort: searchParams.get('sort') || 'createdAt-desc',
    page: parseInt(searchParams.get('page')) || 1
  });

  const { data, isLoading, error } = useQuery(
    ['search-gigs', filters],
    () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      return axios.get(`/api/gigs?${params}`).then(res => res.data);
    },
    { keepPreviousData: true }
  );

  useEffect(() => {
    const newParams = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) newParams.set(key, value.toString());
    });
    setSearchParams(newParams);
  }, [filters, setSearchParams]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1 // Reset to first page when filters change
    }));
  };

  const handlePageChange = (page) => {
    setFilters(prev => ({ ...prev, page }));
    window.scrollTo(0, 0);
  };

  const gigs = data?.gigs || [];
  const totalPages = data?.totalPages || 0;
  const currentPage = data?.currentPage || 1;

  return (
    <SearchContainer>
      <SearchHeader>
        <SearchTitle>
          {filters.q ? `Search results for "${filters.q}"` : 'All Services'}
        </SearchTitle>
        <SearchResults>
          {data?.total || 0} services found
        </SearchResults>
      </SearchHeader>

      <SearchContent>
        <Filters>
          <FilterGroup>
            <FilterTitle>Search</FilterTitle>
            <FilterInput
              type="text"
              placeholder="Search services..."
              value={filters.q}
              onChange={(e) => handleFilterChange('q', e.target.value)}
            />
          </FilterGroup>

          <FilterGroup>
            <FilterTitle>Category</FilterTitle>
            <FilterSelect
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
            >
              {categories.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </FilterSelect>
          </FilterGroup>

          <FilterGroup>
            <FilterTitle>Price Range</FilterTitle>
            <FilterInput
              type="number"
              placeholder="Min price"
              value={filters.minPrice}
              onChange={(e) => handleFilterChange('minPrice', e.target.value)}
              min="0"
            />
            <FilterInput
              type="number"
              placeholder="Max price"
              value={filters.maxPrice}
              onChange={(e) => handleFilterChange('maxPrice', e.target.value)}
              min="0"
            />
          </FilterGroup>

          <FilterGroup>
            <FilterTitle>Delivery Time</FilterTitle>
            <FilterSelect
              value={filters.deliveryTime}
              onChange={(e) => handleFilterChange('deliveryTime', e.target.value)}
            >
              <option value="">Any time</option>
              <option value="1">Up to 1 day</option>
              <option value="3">Up to 3 days</option>
              <option value="7">Up to 7 days</option>
              <option value="14">Up to 14 days</option>
            </FilterSelect>
          </FilterGroup>

          <FilterGroup>
            <FilterTitle>Sort By</FilterTitle>
            <FilterSelect
              value={filters.sort}
              onChange={(e) => handleFilterChange('sort', e.target.value)}
            >
              {sortOptions.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </FilterSelect>
          </FilterGroup>
        </Filters>

        <div>
          {isLoading ? (
            <div className="loading">Loading services...</div>
          ) : error ? (
            <div className="error">Error loading services</div>
          ) : gigs.length === 0 ? (
            <div className="text-center">
              <p>No services found matching your criteria.</p>
              <button 
                onClick={() => setFilters({
                  q: '',
                  category: '',
                  minPrice: '',
                  maxPrice: '',
                  deliveryTime: '',
                  sort: 'createdAt-desc',
                  page: 1
                })}
                className="btn btn-primary"
              >
                Clear Filters
              </button>
            </div>
          ) : (
            <>
              <GigGrid>
                {gigs.map(gig => (
                  <GigCard key={gig._id} gig={gig} />
                ))}
              </GigGrid>

              {totalPages > 1 && (
                <Pagination>
                  <PageButton
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </PageButton>
                  
                  {[...Array(totalPages)].map((_, index) => {
                    const page = index + 1;
                    if (
                      page === 1 || 
                      page === totalPages || 
                      (page >= currentPage - 1 && page <= currentPage + 1)
                    ) {
                      return (
                        <PageButton
                          key={page}
                          onClick={() => handlePageChange(page)}
                          className={page === currentPage ? 'active' : ''}
                        >
                          {page}
                        </PageButton>
                      );
                    } else if (page === currentPage - 2 || page === currentPage + 2) {
                      return <span key={page}>...</span>;
                    }
                    return null;
                  })}
                  
                  <PageButton
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </PageButton>
                </Pagination>
              )}
            </>
          )}
        </div>
      </SearchContent>
    </SearchContainer>
  );
};

export default Search;