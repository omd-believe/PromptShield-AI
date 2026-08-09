package com.promptshield.backend.repository;

import com.promptshield.backend.entity.Prompt;
import com.promptshield.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PromptRepository extends JpaRepository<Prompt, Long> {

    List<Prompt> findByUser(User user);

    List<Prompt> findByUserOrderByCreatedAtDesc(User user);

    Optional<Prompt> findByPromptIdAndUser(Long promptId, User user);

}
