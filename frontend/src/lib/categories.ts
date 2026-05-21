/**
 * Shared concept category definitions.
 * Extracted from CategorySelect so page files only export React components
 * (required by react-refresh/only-export-components).
 */

export interface ConceptCategory {
  id: string
  label: string
  icon: string
  examples: string[]
}

export const CONCEPT_CATEGORIES: ConceptCategory[] = [
  { id: 'software_tech', label: 'Software & Tech', icon: '\u{1F4BB}', examples: ['Apps', 'SaaS', 'APIs', 'Tools'] },
  { id: 'physical_product', label: 'Physical Product', icon: '\u{1F4E6}', examples: ['Gadgets', 'Hardware', 'Consumer goods'] },
  { id: 'built_environment', label: 'Built Environment', icon: '\u{1F3D7}️', examples: ['Architecture', 'Interiors', 'Spaces'] },
  { id: 'business_startup', label: 'Business & Startup', icon: '\u{1F680}', examples: ['Ventures', 'Franchises', 'Services'] },
  { id: 'creative_writing', label: 'Creative Writing', icon: '✍️', examples: ['Novels', 'Scripts', 'Stories'] },
  { id: 'research_academic', label: 'Research & Academic', icon: '\u{1F52C}', examples: ['Papers', 'Studies', 'Experiments'] },
  { id: 'art_visual', label: 'Art & Visual', icon: '\u{1F3A8}', examples: ['Design', 'Photography', 'Illustration'] },
  { id: 'music_audio', label: 'Music & Audio', icon: '\u{1F3B5}', examples: ['Albums', 'Podcasts', 'Compositions'] },
  { id: 'film_video', label: 'Film & Video', icon: '\u{1F3AC}', examples: ['Films', 'YouTube', 'Documentaries'] },
  { id: 'food_hospitality', label: 'Food & Hospitality', icon: '\u{1F37D}️', examples: ['Restaurants', 'Cafes', 'Catering'] },
  { id: 'fashion_apparel', label: 'Fashion & Apparel', icon: '\u{1F457}', examples: ['Clothing', 'Brands', 'Collections'] },
  { id: 'education_training', label: 'Education & Training', icon: '\u{1F4DA}', examples: ['Courses', 'Workshops', 'Bootcamps'] },
  { id: 'event_experience', label: 'Event & Experience', icon: '\u{1F3AA}', examples: ['Festivals', 'Conferences', 'Pop-ups'] },
  { id: 'health_wellness', label: 'Health & Wellness', icon: '\u{1F4AA}', examples: ['Fitness', 'Therapy', 'Wellness'] },
  { id: 'social_impact', label: 'Social Impact', icon: '\u{1F30D}', examples: ['Nonprofits', 'Community', 'Advocacy'] },
  { id: 'finance_investment', label: 'Finance & Investment', icon: '\u{1F4B0}', examples: ['Fintech', 'Investing', 'Budgeting'] },
]
