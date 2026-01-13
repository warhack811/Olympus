# Implementation Plan: Persona UI Improvement

## Overview

Atlas projesinde persona seçimi UI'ını input-integrated çözümü ile iyileştirme. Mevcut footer'daki persona pills sistemini input alanının içine entegre ederek footer'da hiç ekstra yer kaplamayan, çok daha şık ve modern bir çözüm implementasyonu.

## Tasks

- [ ] 1. Persona konfigürasyon sistemi oluştur
  - Create persona configuration object with icons, names, short names, descriptions
  - Define persona color mapping for visual consistency
  - Set up persona state management utilities
  - Add short name mappings for compact display (e.g., "Standart" → "Std")
  - _Requirements: 4.1, 4.3_

- [ ] 1.1 Write property test for persona configuration
  - **Property 9: Complete Persona Coverage**
  - **Validates: Requirements 4.1**

- [-] 2. Input-integrated HTML yapısını implement et
  - Add persona-input-selector to existing input-wrapper
  - Create persona-input-btn with compact icon + short name + arrow
  - Build persona-input-dropdown with all 9 personas
  - Position selector as first element in input-wrapper
  - Maintain semantic HTML structure for accessibility
  - _Requirements: 1.1, 2.2, 4.1_

- [ ] 2.1 Write property test for HTML structure
  - **Property 9: Complete Persona Coverage**
  - **Validates: Requirements 4.1**

- [-] 3. CSS styling için input-integrated tasarım implement et
  - Create .persona-input-selector styles within input-wrapper
  - Style .persona-input-btn to match input-wrapper aesthetic
  - Design .persona-input-dropdown with proper positioning above input
  - Implement hover states and active states
  - Ensure seamless integration with existing input-wrapper design
  - Remove old persona-pills-container styles
  - _Requirements: 1.2, 3.1, 3.2_

- [ ] 3.1 Write property test for space utilization
  - **Property 1: Kompakt Alan Kullanımı**
  - **Validates: Requirements 1.2**

- [ ] 3.2 Write property test for visual consistency
  - **Property 7: Visual Consistency**
  - **Validates: Requirements 3.1, 3.2**

- [ ] 4. Responsive design ve mobile optimization
  - Implement mobile-specific styles for input-integrated selector
  - Ensure touch-friendly button sizes within input constraints
  - Add mobile dropdown positioning logic (above input)
  - Test viewport adaptability with input-wrapper
  - _Requirements: 2.4_

- [ ] 4.1 Write property test for responsive behavior
  - **Property 6: Responsive Behavior**
  - **Validates: Requirements 2.4**

- [-] 5. JavaScript functionality implement et
  - Create togglePersonaInput() function
  - Update selectPersona() for new input-integrated UI structure
  - Implement dropdown open/close logic with input-wrapper context
  - Add click outside to close functionality
  - Maintain backward compatibility with existing functions
  - _Requirements: 2.1, 5.1_

- [ ] 5.1 Write property test for accessibility
  - **Property 3: Erişilebilirlik Garantisi**
  - **Validates: Requirements 2.1**

- [ ] 5.2 Write property test for JavaScript compatibility
  - **Property 11: JavaScript Compatibility**
  - **Validates: Requirements 5.1**

- [ ] 6. Keyboard navigation ve accessibility
  - Implement Tab navigation through persona options
  - Add Enter/Space key handlers for selection
  - Implement Arrow key navigation in dropdown
  - Add ARIA labels and semantic attributes
  - Test screen reader compatibility
  - _Requirements: 2.2_

- [ ] 6.1 Write property test for keyboard navigation
  - **Property 4: Keyboard Navigation Desteği**
  - **Validates: Requirements 2.2**

- [ ] 7. Animasyon ve transitions ekle
  - Implement smooth dropdown open/close animations
  - Add persona selection transition effects
  - Create hover animation for persona options
  - Respect prefers-reduced-motion setting
  - _Requirements: 3.3_

- [ ] 7.1 Write property test for smooth animations
  - **Property 8: Smooth Animations**
  - **Validates: Requirements 3.3**

- [ ] 8. Hover tooltips ve feedback sistemi
  - Create persona description tooltips on hover
  - Implement tooltip positioning logic
  - Add visual feedback for interactive elements
  - Style tooltips with Atlas theme
  - _Requirements: 2.3_

- [ ] 8.1 Write property test for hover feedback
  - **Property 5: Hover Feedback**
  - **Validates: Requirements 2.3**

- [ ] 9. Backend integration ve state management
  - Ensure persona selection sends to backend correctly
  - Implement error handling for backend failures
  - Add retry logic for failed persona updates
  - Preserve chat history during persona changes
  - _Requirements: 4.4, 5.3_

- [ ] 9.1 Write property test for backend integration
  - **Property 10: Backend Integration**
  - **Validates: Requirements 4.4**

- [ ] 9.2 Write property test for state preservation
  - **Property 13: State Preservation**
  - **Validates: Requirements 5.3**

- [ ] 10. Performance optimization
  - Minimize CSS bundle impact
  - Optimize JavaScript execution
  - Implement lazy loading for dropdown content
  - Measure and ensure <5% performance impact
  - _Requirements: 5.2_

- [ ] 10.1 Write property test for performance
  - **Property 12: Performance Preservation**
  - **Validates: Requirements 5.2**

- [ ] 11. Cross-browser compatibility testing
  - Test in Chrome, Firefox, Safari, Edge
  - Implement fallbacks for older browsers
  - Test mobile browsers (iOS Safari, Chrome Mobile)
  - Ensure graceful degradation
  - _Requirements: 5.4_

- [ ] 12. Integration ve final testing
  - Test with existing chat functionality
  - Verify footer layout stability
  - Test session management integration
  - Ensure no conflicts with other UI components
  - _Requirements: 5.1, 5.3_

- [x] 13. Cleanup ve legacy code removal
  - Remove old persona-pills-container HTML completely
  - Clean up unused CSS from atlas-footer.css (persona-pills styles)
  - Update JavaScript exports and references
  - Remove deprecated persona dropdown functions
  - Update HTML to remove persona-pills-container section
  - _Requirements: 5.1_

- [ ] 14. Final checkpoint - Comprehensive testing
  - Run all property-based tests
  - Verify all requirements are met
  - Test complete user workflows with input-integrated persona selector
  - Test input-wrapper layout stability
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Focus on seamless integration with existing input-wrapper design
- Input-integrated approach eliminates footer space usage completely